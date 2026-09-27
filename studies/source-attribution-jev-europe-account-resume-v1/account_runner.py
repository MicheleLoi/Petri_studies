"""Bounded fallback amendment: copied frozen engine with explicit, bounded policy changes.

Raw historical requests, responses, results and suspension are never rewritten.
The original repair plan/payloads remain identical; POLICY.json records the override.
"""
import sys
from pathlib import Path
SIBLINGS=Path(__file__).resolve().parent.parent
BASE=SIBLINGS/'source-attribution-jev-europe-repair-v1'
PACING=SIBLINGS/'source-attribution-jev-europe-pacing-v1'
sys.path.insert(0,str(BASE/'code'))
sys.path.insert(0,str(PACING))
from main_runner import *
import main_runner as original
from paced_runner import PacedTransport
PACKAGE=Path(__file__).resolve().parent
POLICY=load(PACKAGE/'POLICY.json')
ROUTING=SIBLINGS/'source-attribution-jev-europe-routing-v1'
sys.path.insert(0,str(ROUTING))
import route_runner as previous
FALLBACK=SIBLINGS/'source-attribution-jev-europe-fallback-v1'
sys.path.insert(0,str(FALLBACK))
import fallback_runner as previous_fallback

def gateway_policy(routing, plan):
    """Only a documented same-model, two-attempt technical failover is added."""
    models=routing.get('modelAttempts',[])
    entries=[]
    if isinstance(models,list):
        for m in models:
            attempts=m.get('providerAttempts') if isinstance(m,dict) else None
            if isinstance(attempts,list):entries.extend(a for a in attempts if isinstance(a,dict))
    internal429=any(a.get('statusCode')==429 for a in entries)
    if internal429:return False,True
    if type(routing.get('totalProviderAttemptCount')) is not int:return False,False
    if routing['totalProviderAttemptCount']==1:return True,False
    if routing['totalProviderAttemptCount']!=2:return False,False
    if type(routing.get('modelAttemptCount')) is not int or routing['modelAttemptCount']!=1 or not isinstance(models,list) or len(models)!=1:return False,False
    m=models[0]
    if not isinstance(m,dict) or m.get('canonicalSlug') not in ('typesafe-ai/jev',plan['jev_presumed_version']) or m.get('success') is not True:return False,False
    if type(m.get('providerAttemptCount')) is not int or m['providerAttemptCount']!=2:return False,False
    attempts=m.get('providerAttempts')
    if not isinstance(attempts,list) or len(attempts)!=2 or not all(isinstance(a,dict) for a in attempts):return False,False
    a,b=attempts
    if any(x.get('provider') not in POLICY['allowed_providers'] for x in attempts):return False,False
    if a.get('success') is not False or type(a.get('statusCode')) is not int or a['statusCode'] not in POLICY['allowed_prior_failures']:return False,False
    if b.get('success') is not True or type(b.get('statusCode')) is not int or b['statusCode']!=200 or routing.get('finalProvider')!=b['provider']:return False,False
    timestamps=[a.get('startTime'),a.get('endTime'),b.get('startTime'),b.get('endTime')]
    if not all(type(t) in (int,float) and __import__('math').isfinite(t) for t in timestamps) or timestamps!=sorted(timestamps):return False,False
    return True,False

def assess(model,envelope,plan):
    r=previous.assess(model,envelope,plan)
    routing=r.get('gateway_metadata',{}).get('routing',{})
    accepted,internal429=gateway_policy(routing,plan)
    if internal429:
        r.update(internal_http429=True,pause_model=True,status='pause')
        r['flags'].append('gateway_internal_http429')
    elif accepted and routing.get('totalProviderAttemptCount')==2 and r.get('identity_accepted'):
        r['flags']=[f for f in r['flags'] if f!='gateway_upstream_attempt_count_not_one']
        r['pause_model']=not r['legend_matches'] or r['score_distribution_consistent'] is False
        r['status']='pause' if r['pause_model'] else ('ok' if r['rating_usable'] else 'retry')
        r['fallback_policy']='jev-europe-fallback-v1'
    return r

def compute(study_root,planned_eur=0):
    """Preserve the original ledger and add a cautious reserve for failed internal calls."""
    result=original.compute(study_root,planned_eur=planned_eur)
    failures=0
    for path in (Path(study_root)/'runs/registered-jev-europe-v1').glob('attempts/*/*/result.json'):
        routing=load(path).get('gateway_metadata',{}).get('routing',{})
        for m in routing.get('modelAttempts',[]):
            if not isinstance(m,dict):continue
            attempts=m.get('providerAttempts',[])
            if isinstance(attempts,list):failures+=sum(isinstance(a,dict) and a.get('success') is False for a in attempts)
    reserve=failures*.01
    result['original_ledger_planning_eur']=result['planning_eur']
    result['upstream_uncertain_reserve_eur']=reserve
    result['planning_eur']+=reserve;result['projected_eur']+=reserve
    result['user_notice_required']=result['projected_eur']>=result['threshold_eur']
    result['early_warning']=result['early_warning'] or result['projected_eur']>=.8*result['threshold_eur']
    return result

def historical_view(run,path,r):
    rel=path.relative_to(Path(run)).as_posix()
    if rel==POLICY['reviewed_access_result']:
        if file_sha(path)!=POLICY['reviewed_access_result_sha256']:raise ValueError('Access review hash mismatch')
        if r.get('http_status')!=403 or r.get('error_code')!='no_providers_available' or r.get('rating_usable') or not r.get('pause_model'):raise ValueError('Wrong access failure')
        reviewed=dict(r)
        reviewed.update(pause_model=False,status='retry',historical_access_review='Author-authorized retry after account credit check; raw403 and attempt count retained')
        return reviewed
    if rel!=POLICY['accepted_fallback_result']:return previous.historical_view(run,path,r)
    if file_sha(path)!=POLICY['accepted_fallback_result_sha256']:raise ValueError('Historical fallback review hash mismatch')
    if r['flags']!=['gateway_upstream_attempt_count_not_one'] or not r['rating_usable'] or not r['identity_accepted']:raise ValueError('Wrong historical fallback flag')
    # The public hash binds the already inspected503->200 sequence, never a new outcome.
    reviewed=dict(r)
    reviewed.update(pause_model=False,status='ok',flags=[],historical_fallback_review='Accepted after acquisition under published fallback amendment; raw flag retained')
    return reviewed

def released_route_suspension(run,model):
    p=Path(run)/'route_suspensions'/f'{model}.json'
    return p.exists() and p.relative_to(Path(run)).as_posix()==POLICY['released_route_suspension'] and file_sha(p)==POLICY['released_route_suspension_sha256']

def released_suspension(run,model):
    p=Path(run)/'suspensions'/f'{model}.json'
    return p.exists() and p.relative_to(Path(run)).as_posix()==POLICY['released_suspension'] and file_sha(p)==POLICY['released_suspension_sha256']

def released_fallback_suspension(run,model):
    p=Path(run)/'fallback_suspensions'/f'{model}.json'
    return p.exists() and p.relative_to(Path(run)).as_posix()==POLICY['released_fallback_suspension'] and file_sha(p)==POLICY['released_fallback_suspension_sha256']


def history(run, row, plan, recover=False):
    results=[]
    requests_found=attempt_dirs(run,row['slot'])
    if len(requests_found)>attempt_limit(plan,row): raise ValueError('Attempt budget exceeded on disk')
    for n,p in enumerate(requests_found,1):
        if any(result['rating_usable'] for result in results):
            raise ValueError('Request follows an already usable slot rating')
        req=load(p)
        spec=plan['payloads'][row['cell']][row['model']]
        if p.parent.name!=f'{n:02}' or req['row']!=row or req['attempt']!=n or req['spec']!=spec:
            raise ValueError('Recorded attempt identity/input changed')
        result_file=p.with_name('result.json')
        if result_file.exists():
            r=load(result_file)
            if r['request_sha256']!=file_sha(p): raise ValueError('Request hash mismatch')
            if r.get('response_sha256') and r['response_sha256']!=file_sha(p.with_name('response.json')):
                raise ValueError('Response hash mismatch')
        elif p.with_name('response.json').exists():
            envelope=load(p.with_name('response.json'))
            r=finish_result(req,p,envelope,plan)
            r['recovered_from_saved_response']=True
            if recover: save(result_file,r)
        else:
            r=dict(status='retry',category='technical',rating_usable=False,rating=None,pause_model=False,
                flags=['uncertain_interrupted_attempt'],billing_estimate_usd=None,
                reserved_eur=req['reserved_eur'],request_sha256=file_sha(p),attempt=n,
                started_utc=req['logged_before_dispatch_utc'],finished_utc=req['logged_before_dispatch_utc'],
                not_before_utc=(datetime.fromisoformat(req['logged_before_dispatch_utc'])+timedelta(seconds=4)).isoformat())
            if recover: save(result_file,r)
        if result_file.exists(): r=historical_view(run,result_file,r)
        results.append(r)
    return results


def finish_result(req, path, envelope, plan):
    r=assess(req['row']['model'],envelope,plan)
    if envelope.get('credential_redaction'):
        r['pause_model']=True; r['status']='pause'; r['flags'].append('credential_echo_redacted')
    finished=envelope['finished_utc']
    base=plan['retry_delays_seconds'][min(req['attempt']-1,1)]
    hdr={k.lower():v for k,v in envelope.get('headers',{}).items()}
    wait,invalid=retry_wait(hdr.get('retry-after'),base,finished)
    if invalid: r['flags'].append('invalid_retry_after')
    r.update(request_sha256=file_sha(path),response_sha256=file_sha(path.with_name('response.json')),
        attempt=req['attempt'],started_utc=req['logged_before_dispatch_utc'],finished_utc=finished,
        reserved_eur=req['reserved_eur'],http_status=envelope['http_status'],response_headers=envelope.get('headers',{}),
        retry_wait_seconds=wait,not_before_utc=(datetime.fromisoformat(finished)+timedelta(seconds=wait)).isoformat())
    return r


class Engine:
    def __init__(self, plan, run, transport, *, budget_check, amendment_receipt, resume_authorization=None, sleeper=time.sleep, clock=now):
        self.plan=plan; self.run=Path(run); self.transport=transport
        self.budget_check=budget_check; self.sleeper=sleeper; self.clock=clock
        self.receipt=amendment_receipt; self.resume_authorization=resume_authorization
        self.budget_stopped=False
        self.mutex=threading.RLock(); self.stop=threading.Event()
        self.paused=set(); self.invocation=uuid.uuid4().hex

    def log(self, kind, **fields):
        with self.mutex:
            save(self.run/'operations'/f'{self.clock().replace(":","-")}-{uuid.uuid4().hex}.json',
                 dict(kind=kind,timestamp_utc=self.clock(),invocation=self.invocation,**fields))

    def hold(self,row,attempt,path,result):
        digest=file_sha(path);target=self.run/'global_holds'/f'{digest}.json'
        if not target.exists():
            save(target,dict(reason='New HTTP 429: collector stopped globally',slot=row['slot'],attempt=attempt,
                request_sha256=digest,timestamp_utc=result['finished_utc'],requires_explicit_dated_release=True))
            self.log('global_http_429_hold',slot=row['slot'],attempt=attempt,hold_sha256=file_sha(target))
        if target in unresolved_holds(self.run):self.stop.set()

    def suspend(self, model, reason):
        with self.mutex:
            affected=next(configs for configs in self.plan['worker_groups'].values() if model in configs)
            for config in affected:
                self.paused.add(config)
                p=self.run/'account_suspensions'/f'{config}.json'
                if not p.exists(): save(p,dict(model=config,trigger_model=model,reason=reason,timestamp_utc=self.clock()))
        self.log('model_suspended',model=model,reason=reason)

    def wait_until(self, deadline):
        started=self.clock()
        while not self.stop.is_set():
            left=(datetime.fromisoformat(deadline)-datetime.fromisoformat(self.clock())).total_seconds()
            if left<=0: break
            self.sleeper(min(left,10))
        self.log('retry_wait',not_before_utc=deadline,started_utc=started,ended_utc=self.clock())

    def slot(self,row):
        m=row['model']
        h=history(self.run,row,self.plan,recover=True)
        if any(r['pause_model'] for r in h): self.suspend(m,'Persisted attempt requires review'); return
        if any(r['rating_usable'] for r in h) or len(h)==attempt_limit(self.plan,row): return
        while len(h)<attempt_limit(self.plan,row) and m not in self.paused and not self.stop.is_set():
            if h: self.wait_until(h[-1]['not_before_utc'])
            if self.stop.is_set(): return
            try:
                auth=self.transport.prepare(m)
            except Exception as e:
                # Auth/token refresh is not a model inference attempt.
                self.suspend(m,'Credential preparation failed: '+type(e).__name__); return
            n=len(h)+1
            p=self.run/'attempts'/row['slot']/f'{n:02}'/'request.json'
            spec=self.plan['payloads'][row['cell']][m]
            with self.mutex:
                reserve=self.plan['reserve_eur_per_model'][m]
                if not self.budget_check(reserve):
                    self.budget_stopped=True; self.stop.set(); self.log('budget_notice_required',slot=row['slot']); return
                req=dict(row=row,attempt=n,spec=spec,spec_sha256=sha(spec),
                    logged_before_dispatch_utc=self.clock(),reserved_eur=reserve,
                    amendment_manifest_sha256=self.receipt['manifest_sha256'],route_manifest_sha256=POLICY['routing_manifest_sha256'],fallback_manifest_sha256=POLICY['fallback_manifest_sha256'],account_manifest_sha256=file_sha(PACKAGE/'MANIFEST.json'))
                if datetime.fromisoformat(req['logged_before_dispatch_utc'])<=datetime.fromisoformat(self.receipt['registered_utc']):
                    raise ValueError('New attempt must follow amendment publication')
                save(p,req)  # irrevocable attempt reservation before any send
            timeout=(self.plan['timeout_connect_seconds'], self.plan['reasoning_timeout_read_seconds'] if m.endswith('_reasoning') else self.plan['timeout_read_seconds'])
            try:
                envelope=self.transport.send(spec,auth,timeout)
                envelope['finished_utc']=self.clock()
                save(p.with_name('response.json'),envelope)
                r=finish_result(req,p,envelope,self.plan)
            except requests.RequestException as e:
                # Do not log exception text: it can include headers or credential-bearing URLs.
                retry=isinstance(e,(requests.Timeout,requests.ConnectionError)) and not isinstance(e,requests.exceptions.SSLError)
                finished=self.clock()
                r=dict(status='retry' if retry else 'pause', category='technical',rating_usable=False,rating=None,
                    pause_model=not retry,flags=['transport_'+type(e).__name__],billing_estimate_usd=None,
                    request_sha256=file_sha(p),attempt=n,reserved_eur=req['reserved_eur'],
                    started_utc=req['logged_before_dispatch_utc'],finished_utc=finished,
                    not_before_utc=(datetime.fromisoformat(finished)+timedelta(seconds=self.plan['retry_delays_seconds'][min(n-1,1)])).isoformat())
            # Unexpected programming/filesystem errors escape: do not continue spending.
            with self.mutex: save(p.with_name('result.json'),r)
            self.log('attempt_completed',slot=row['slot'],attempt=n,status=r['status'],
                     category=r['category'],rating_usable=r['rating_usable'])
            if r.get('http_status')==429 or r.get('internal_http429'):
                self.hold(row,n,p,r); return
            if r['pause_model']: self.suspend(m,'Review result '+str(p.with_name('result.json').relative_to(self.run))); return
            if r['rating_usable']: return
            h.append(r)

    def model_block(self, rows):
        try:
            for row in rows:
                if row['model'] in self.paused or self.stop.is_set(): break
                self.slot(row)
        except BaseException:
            self.stop.set()
            raise

    def execute(self):
        with exclusive(self.run):
            release=self.run/'account_policy_release.json'
            if release.exists():
                if load(release)['policy']!=POLICY: raise ValueError('Route release policy mismatch')
            else: save(release,dict(policy=POLICY,timestamp_utc=self.clock(),raw_suspension_preserved=True))
            verify_run_lineage(self.plan,self.run,self.receipt)
            if (self.run/'finished.json').exists(): return load(self.run/'finished.json')
            digest=sha(self.plan)
            marker=self.run/'repair_started.json'
            if marker.exists():
                if load(marker)['plan_sha256']!=digest: raise ValueError('Repair plan changed on resume')
            else: save(marker,dict(plan_sha256=digest,amendment_manifest_sha256=self.receipt['manifest_sha256'],timestamp_utc=self.clock()))
            saved=self.run/'amendment_launch_record.json'
            if saved.exists():
                if load(saved)['manifest_sha256']!=self.receipt['manifest_sha256']: raise ValueError('Different amendment receipt')
            else: save(saved,self.receipt)
            if self.resume_authorization is not None:
                record_hold_release(self.run,self.resume_authorization,self.clock())
            self.log('execution_opened',pid=os.getpid(),plan_sha256=digest)
            for m in self.plan['models']:
                if ((self.run/'suspensions'/f'{m}.json').exists() and not released_suspension(self.run,m)) or ((self.run/'route_suspensions'/f'{m}.json').exists() and not released_route_suspension(self.run,m)) or ((self.run/'fallback_suspensions'/f'{m}.json').exists() and not released_fallback_suspension(self.run,m)) or (self.run/'account_suspensions'/f'{m}.json').exists(): self.paused.add(m)
            # Reconstruct the whole history before any new inference, including crashes
            # after a response was saved but before its pause flag was persisted.
            for row in self.plan['schedule']:
                h=history(self.run,row,self.plan,recover=True)
                for r in h:
                    rel=f"attempts/{row['slot']}/{r['attempt']:02}/request.json"
                    if (r.get('http_status')==429 or r.get('internal_http429')) and rel not in self.plan['amendment']['preserved_prefix']['files']:
                        self.hold(row,r['attempt'],self.run/rel,r)
                if any(r['pause_model'] for r in h) and row['model'] not in self.paused:
                    self.suspend(row['model'],'Persisted/recovered response requires review before resumption')
            if unresolved_holds(self.run): self.stop.set()
            with ThreadPoolExecutor(max_workers=self.plan['parallel_workers']) as pool:
                for block in range(1,self.plan['blocks']+1):
                    if self.stop.is_set(): break
                    rows=[r for r in self.plan['schedule'] if r['block']==block and r['model'] not in self.paused]
                    planned=0
                    for row in rows:
                        h=history(self.run,row,self.plan)
                        if not any(r['rating_usable'] for r in h): planned+=(attempt_limit(self.plan,row)-len(h))*self.plan['reserve_eur_per_model'][row['model']]
                    if not self.budget_check(planned):
                        self.log('budget_notice_required',block=block,planned_batch_eur=planned); self.budget_stopped=True; self.stop.set(); break
                    self.log('block_opened',block=block,planned_batch_reserve_eur=planned)
                    futures=[pool.submit(self.model_block,[r for r in rows if r['worker_group']==group]) for group in self.plan['worker_groups']]
                    for f in futures: f.result()
                    self.log('block_closed',block=block,paused_models=sorted(self.paused))
            terminal=0; usable=0
            for row in self.plan['schedule']:
                h=history(self.run,row,self.plan)
                has=any(r['rating_usable'] for r in h)
                terminal+=has or len(h)==attempt_limit(self.plan,row); usable+=has
            result=dict(timestamp_utc=self.clock(),planned_slots=len(self.plan['schedule']),terminal_slots=terminal,
                usable_slots=usable,paused_models=sorted(self.paused),budget_stopped=self.budget_stopped,
                global_hold=bool(unresolved_holds(self.run)),amendment_id=self.plan['amendment']['id'],
                complete=terminal==len(self.plan['schedule']) and not self.paused and not unresolved_holds(self.run))
            self.log('execution_closed',**{k:v for k,v in result.items() if k!='timestamp_utc'})
            if result['complete']: save(self.run/'finished.json',result)
            return result

def verify_route_package():
    previous_fallback.verify_route_package()
    if file_sha(FALLBACK/'MANIFEST.json')!=POLICY['fallback_manifest_sha256']:raise ValueError('Fallback package changed')
    for rel,digest in load(PACKAGE/'MANIFEST.json')['files'].items():
        p=(PACKAGE/rel).resolve()
        if not p.is_relative_to(PACKAGE) or file_sha(p)!=digest:raise ValueError('Route package changed: '+rel)
    if file_sha(ROUTING/'MANIFEST.json')!=POLICY['routing_manifest_sha256']:raise ValueError('Routing package changed')
    for rel,digest in load(ROUTING/'MANIFEST.json')['files'].items():
        if file_sha(ROUTING/rel)!=digest:raise ValueError('Routing code changed')
    if file_sha(BASE/'MANIFEST.json')!=POLICY['base_manifest_sha256']:raise ValueError('Base package changed')
    if file_sha(PACING/'MANIFEST.json')!=POLICY['pacing_manifest_sha256']:raise ValueError('Pacing package changed')
    for rel,digest in load(PACING/'MANIFEST.json')['files'].items():
        if file_sha(PACING/rel)!=digest:raise ValueError('Pacing code changed')

def verify_prefix(run):
    for rel,digest in load(PACKAGE/'PRESERVED_PREFIX.json')['files'].items():
        if file_sha(Path(run)/rel)!=digest:raise ValueError('Historical prefix changed: '+rel)

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--study-root',type=Path,required=True)
    cli.add_argument('--launch-record',type=Path,required=True)
    cli.add_argument('--account-record',type=Path,required=True)
    a=cli.parse_args()
    verify_route_package()
    receipt=load(a.account_record)
    if receipt['manifest_sha256']!=file_sha(PACKAGE/'MANIFEST.json') or receipt['visibility']!='public':raise ValueError('Wrong public route receipt')
    if not receipt['registration_reference'] or datetime.fromisoformat(receipt['registered_utc'])>=datetime.now(timezone.utc):raise ValueError('Invalid publication time')
    plan,_,original_receipt=verify_launch(BASE,a.launch_record)
    if plan['parallel_workers']!=1 or len(plan['worker_groups'])!=1:raise ValueError('Pacing requires one worker')
    run=a.study_root/'runs'/plan['run_id'];verify_prefix(run)
    results=[datetime.fromisoformat(load(p)['finished_utc']) for p in run.glob('attempts/*/*/result.json')]
    wait=max(0,60-(datetime.now(timezone.utc)-max(results)).total_seconds()) if results else 0
    transport=PacedTransport(HttpTransport(),wait)
    engine=Engine(plan,run,transport,budget_check=lambda x:not compute(a.study_root,planned_eur=x)['user_notice_required'],amendment_receipt=original_receipt)
    transport.log=engine.log
    save(run/'account_launch_checks'/(now().replace(':','-')+'.json'),dict(receipt=receipt,recorded_utc=now()))
    save(run/'launch_checks'/(now().replace(':','-')+'-account-docs.json'),original_receipt)
    print(json.dumps(engine.execute()),flush=True)

if __name__=='__main__':main()
