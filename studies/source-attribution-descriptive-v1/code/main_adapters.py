"""Prospective provider parsing and explicit one-send transport. No network on import."""
import json
import math
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import requests
from response_quality import assess_response
from design import duplicate_guard
from trace import canonical


def decode(raw):
    def bad(value):
        raise ValueError('Non-finite JSON')
    d = json.loads(raw, object_pairs_hook=duplicate_guard, parse_constant=bad)
    if not isinstance(d, dict):
        raise ValueError('Expected response object')
    return d


def number(value, lo=0, hi=float('inf')):
    return type(value) in (int,float) and lo <= value <= hi and math.isfinite(value)


def retry_wait(header, base, timestamp):
    if header is None:
        return base, False
    try:
        try:
            delay = float(header)
        except ValueError:
            when = parsedate_to_datetime(header)
            if when.tzinfo is None:
                raise ValueError('No timezone')
            delay = (when-datetime.fromisoformat(timestamp)).total_seconds()
        if not math.isfinite(delay):
            raise ValueError('Invalid delay')
        return max(base, delay, 0), False
    except (TypeError, ValueError, OverflowError):
        return base, True


def assess(model, envelope, plan):
    """Keep measurement usability separate from version/suspension flags."""
    r = dict(rating_usable=False, rating=None, pause_model=False, flags=[],
             billing_estimate_usd=None, returned_model=None, response_text=None,
             category='missing_rating', status='retry', usage=None)
    raw = envelope.get('body','')
    try:
        d = decode(raw)
    except (ValueError, TypeError, RecursionError):
        d = None
    status = envelope.get('http_status')
    if status != 200:
        err = d.get('error', {}) if isinstance(d,dict) else {}
        if not isinstance(err,dict):
            err = {}
        code = str(err.get('code') or err.get('type') or err.get('status') or '')
        permanent = code.lower() in ('insufficient_quota','billing_hard_limit_reached',
            'organization_usage_limit_exceeded','credit_balance_too_low','billing_error')
        retry = status in plan['transient_http'] and not permanent
        r.update(category='technical', status='retry' if retry else 'pause',
                 pause_model=not retry, error_code=code, http_status=status)
        return r
    if d is None:
        # Unreadable success response also lacks verifiable identity.
        r.update(status='pause', pause_model=True, flags=['unreadable_body_identity_unverified'])
        return r
    try:
        if model == 'jev':
            a = d.get('answers',{}).get('argument_strength',{})
            if not isinstance(a,dict): a = {}
            s = a.get('score')
            usable = a.get('type')=='score' and number(s,0,4)
            expected = {str(i):c for i,c in enumerate(plan['payloads'][plan['cells'][0]]['jev']['payload']['questions']['argument_strength']['criteria'])}
            legend = a.get('legend') == expected
            p = a.get('probabilities')
            valid_p = isinstance(p,dict) and set(p)==set(expected) and all(number(v,0,1) for v in p.values())
            valid_p = bool(valid_p and abs(sum(p.values())-1)<=1e-6)
            consistent = abs(sum(int(k)*v for k,v in p.items())-s)<=.025 if valid_p and usable else None
            gateway = d.get('provider_metadata',{}).get('gateway',{})
            routing = gateway.get('routing',{})
            version = d.get('model')
            identity = version in ('typesafe-ai/jev',plan['jev_presumed_version']) and routing.get('finalProvider')=='typesafe-ai'
            r.update(rating_usable=bool(usable and legend), rating=s/4 if usable and legend else None,
                     native_score=s if usable else None, returned_model=version,
                     presumed_model=plan['jev_presumed_version'], version_verified=version==plan['jev_presumed_version'],
                     identity_accepted=identity, legend_matches=legend, probabilities_valid=valid_p,
                     score_distribution_consistent=consistent, confidence=a.get('confidence'),
                     gateway_metadata=gateway, usage=d.get('usage'), structured_answer=a)
            if not valid_p: r['flags'].append('auxiliary_probabilities_invalid_or_missing')
            if not number(a.get('confidence'),0,1): r['flags'].append('confidence_invalid_or_missing')
            if set(a)-{'type','score','confidence','legend','probabilities'}: r['flags'].append('additional_answer_fields')
            if not legend: r['flags'].append('legend_mismatch')
            if consistent is False: r['flags'].append('score_distribution_inconsistent')
            if routing.get('totalProviderAttemptCount') != 1:
                r['flags'].append('gateway_upstream_attempt_count_not_one')
            try:
                cost = float(gateway.get('cost'))
                if number(cost): r['billing_estimate_usd'] = cost
            except (ValueError, TypeError, OverflowError): pass
            r['cost_basis'] = 'gateway reported cost; invoice unverified'
            r['pause_model'] = not identity or not legend or consistent is False or routing.get('totalProviderAttemptCount') != 1
        else:
            if model=='sonnet45':
                text = ''.join(c.get('text','') for c in d.get('content',[]) if c.get('type')=='text')
                version,stop,u = d.get('model'),d.get('stop_reason'),d.get('usage',{})
                ntin,ntout = u.get('input_tokens'),u.get('output_tokens')
                complete = stop=='end_turn'
            elif model=='gpt4o':
                choices = d.get('choices',[])
                c = choices[0] if len(choices)==1 else {}
                text = c.get('message',{}).get('content')
                version,stop,u = d.get('model'),c.get('finish_reason'),d.get('usage',{})
                ntin,ntout = u.get('prompt_tokens'),u.get('completion_tokens')
                complete = stop=='stop'
                r['system_fingerprint'] = d.get('system_fingerprint')
            else:
                candidates = d.get('candidates',[])
                c = candidates[0] if len(candidates)==1 else {}
                text = ''.join(p.get('text','') for p in c.get('content',{}).get('parts',[]) if not p.get('thought',False))
                version,stop,u = d.get('modelVersion'),c.get('finishReason'),d.get('usageMetadata',{})
                ntin = u.get('promptTokenCount')
                ntout = u.get('candidatesTokenCount')
                if number(ntout) and number(u.get('thoughtsTokenCount',0)): ntout += u.get('thoughtsTokenCount',0)
                else: ntout = None
                complete = stop=='STOP'
            q = assess_response(text, generation_complete=complete)
            r.update(rating_usable=q['rating_usable'], rating=q['strength_rating'], response_text=text,
                     quality=q, returned_model=version, stop_reason=stop, usage=u,
                     identity_accepted=version==plan['reference_models'][model],
                     input_tokens=ntin, output_tokens=ntout)
            r['pause_model'] = not r['identity_accepted']
            if not q['schema_conformant']: r['flags'].append('schema_deviation')
            if number(ntin) and number(ntout):
                rates=plan['rates_usd_per_million'][model]
                r['billing_estimate_usd']=(ntin*rates[0]+ntout*rates[1])/1e6
            r['cost_basis']='historical token planning rates; caching/discounts not deducted; invoice unverified'
        if not r['identity_accepted']: r['flags'].append('model_identity_unverified_or_changed')
        r['status']='pause' if r['pause_model'] else ('ok' if r['rating_usable'] else 'retry')
        return r
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        r.update(status='pause',pause_model=True,rating_usable=False,rating=None,
                 flags=r['flags']+['unexpected_provider_schema'])
        return r


class CredentialStore:
    """Explicit existing sources. Values never returned to a diagnostic or file."""
    def __init__(self):
        self.google=None

    def headers(self, model):
        if model=='gpt4o':
            return {'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']}
        if model=='sonnet45':
            return {'x-api-key':os.environ['ANTHROPIC_API_KEY'], 'anthropic-version':'2023-06-01'}
        if model=='jev':
            path=Path.home()/'.config/source-attribution/secrets.env'
            keys=[line.split('=',1)[1].strip().strip('\"\'') for line in path.read_text(encoding='utf-8-sig').splitlines()
                  if '=' in line and line.split('=',1)[0].strip()=='AI_GATEWAY_API_KEY']
            if len(keys)!=1 or not keys[0] or keys[0]=='PASTE_YOUR_KEY_HERE' or any(c.isspace() for c in keys[0]):
                raise ValueError('Invalid gateway credential configuration')
            return {'Authorization':'Bearer '+keys[0]}
        import google.auth
        from google.auth.transport.requests import Request
        if self.google is None:
            self.google,_=google.auth.load_credentials_from_file(str(Path.home()/'.gcloud-adc/application_default_credentials.json'),
                scopes=['https://www.googleapis.com/auth/cloud-platform'])
        if not self.google.valid: self.google.refresh(Request())
        return {'Authorization':'Bearer '+self.google.token,'x-goog-user-project':'app-tracciabile-dev'}


class HttpTransport:
    def __init__(self):
        self.credentials=CredentialStore()

    def prepare(self, model):
        return self.credentials.headers(model)

    def send(self, spec, auth, timeout):
        # Fresh session, no SDK/HTTP retries, no redirects, no cookies across requests.
        with requests.Session() as session:
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=0))
            response=session.post(spec['endpoint'],headers={**auth,'Content-Type':'application/json'},
                data=canonical(spec['payload']),timeout=timeout,allow_redirects=False)
        raw=response.text
        redacted=False
        for name,value in auth.items():
            if name.lower() in ('authorization','x-api-key'):
                secret=value.removeprefix('Bearer ')
                if secret and secret in raw:
                    raw=raw.replace(secret,'[REDACTED_CREDENTIAL]'); redacted=True
        return dict(http_status=response.status_code,body=raw,credential_redaction=redacted,
            headers={k:v for k,v in response.headers.items() if k.lower() in ('request-id','x-request-id','retry-after','date')})
