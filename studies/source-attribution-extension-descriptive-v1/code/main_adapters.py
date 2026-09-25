"""Two-provider extension of the previous transport and rating policy; no import I/O."""
import json
import math
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import requests
from response_quality import assess_response
from design import duplicate_guard
from trace import canonical

def number(x):return type(x) in (int,float) and x>=0 and math.isfinite(x)
def decode(raw):
    def reject(v):raise ValueError('Non-finite JSON')
    d=json.loads(raw,object_pairs_hook=duplicate_guard,parse_constant=reject)
    if not isinstance(d,dict):raise ValueError('Expected response object')
    return d

def retry_wait(header,base,timestamp):
    if header is None:return base,False
    try:
        try:delay=float(header)
        except ValueError:
            when=parsedate_to_datetime(header)
            if when.tzinfo is None:raise ValueError('No timezone')
            delay=(when-datetime.fromisoformat(timestamp)).total_seconds()
        if not math.isfinite(delay):raise ValueError('Invalid delay')
        return max(base,delay,0),False
    except (ValueError,TypeError,OverflowError):return base,True

def assess(model,envelope,plan):
    r=dict(rating_usable=False,rating=None,pause_model=False,flags=[],billing_estimate_usd=None,
           returned_model=None,response_text=None,category='missing_rating',status='retry',usage=None)
    try:d=decode(envelope.get('body',''))
    except (ValueError,TypeError,RecursionError):d=None
    status=envelope.get('http_status')
    if status!=200:
        err=d.get('error',{}) if isinstance(d,dict) else {}
        if not isinstance(err,dict):err={}
        code=str(err.get('code') or err.get('type') or err.get('status') or '')
        permanent=code.lower() in ('insufficient_quota','billing_hard_limit_reached','organization_usage_limit_exceeded','credit_balance_too_low','billing_error')
        retry=status in plan['transient_http'] and not permanent
        r.update(category='technical',status='retry' if retry else 'pause',pause_model=not retry,error_code=code,http_status=status)
        return r
    if d is None:
        r.update(status='pause',pause_model=True,flags=['unreadable_body_identity_unverified']);return r
    try:
        if plan['provider_by_model'][model]=='anthropic':
            text=''.join(c.get('text','') for c in d.get('content',[]) if c.get('type')=='text')
            version,stop,u=d.get('model'),d.get('stop_reason'),d.get('usage',{})
            ni,no=u.get('input_tokens'),u.get('output_tokens');complete=stop=='end_turn'
            r['thinking_block_types']=[c.get('type') for c in d.get('content',[]) if c.get('type')!='text']
        else:
            choices=d.get('choices',[]);c=choices[0] if len(choices)==1 else {}
            text=c.get('message',{}).get('content')
            version,stop,u=d.get('model'),c.get('finish_reason'),d.get('usage',{})
            ni,no=u.get('prompt_tokens'),u.get('completion_tokens');complete=stop=='stop'
            r['system_fingerprint']=d.get('system_fingerprint')
            r['reasoning_tokens_reported']=u.get('completion_tokens_details',{}).get('reasoning_tokens')
        q=assess_response(text,generation_complete=complete)
        identity=version==plan['reference_models'][model]
        r.update(rating_usable=q['rating_usable'],rating=q['strength_rating'],response_text=text,quality=q,
                 returned_model=version,stop_reason=stop,usage=u,identity_accepted=identity,
                 pause_model=not identity,input_tokens=ni,output_tokens=no)
        if not q['schema_conformant']:r['flags'].append('schema_deviation')
        if not identity:r['flags'].append('model_identity_unverified_or_changed')
        if number(ni) and number(no):
            a,b=plan['rates_usd_per_million'][model];r['billing_estimate_usd']=(ni*a+no*b)/1e6
        r['cost_basis']='Full-price usage estimate; invoice unverified; output includes reasoning where charged'
        r['status']='pause' if r['pause_model'] else ('ok' if r['rating_usable'] else 'retry')
        return r
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        r.update(status='pause',pause_model=True,rating_usable=False,rating=None,flags=r['flags']+['unexpected_provider_schema'])
        return r

class HttpTransport:
    def prepare(self,model):
        if model in ('gpt4o','sol','sol_reasoning'):
            return {'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']}
        return {'x-api-key':os.environ['ANTHROPIC_API_KEY'],'anthropic-version':'2023-06-01'}
    def send(self,spec,auth,timeout):
        expected='https://api.openai.com/v1/chat/completions' if spec['provider']=='openai' else 'https://api.anthropic.com/v1/messages'
        if spec['endpoint']!=expected:raise ValueError('Unexpected endpoint')
        with requests.Session() as session:
            session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
            response=session.post(expected,headers={**auth,'Content-Type':'application/json'},
                                  data=canonical(spec['payload']),timeout=timeout,allow_redirects=False)
        raw=response.text;redacted=False
        for name,value in auth.items():
            if name.lower() in ('authorization','x-api-key'):
                secret=value.removeprefix('Bearer ')
                if secret and secret in raw:raw=raw.replace(secret,'[REDACTED_CREDENTIAL]');redacted=True
        return dict(http_status=response.status_code,body=raw,credential_redaction=redacted,
                    headers={k:v for k,v in response.headers.items() if k.lower() in ('request-id','x-request-id','retry-after','date')})
