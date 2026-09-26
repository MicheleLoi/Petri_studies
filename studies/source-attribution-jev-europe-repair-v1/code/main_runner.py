"""Resumable descriptive collection. CLI defaults to offline verification, never execution."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
import time
import uuid
import requests
from main_plan import load, build, validate, attempt_limit
from main_adapters import assess, retry_wait, HttpTransport
from trace import canonical, file_sha, now, sha
from budget import compute


def save(path, obj):
    """Exclusive immutable artifact. A leftover .writing file is not a sent request."""
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.writing')
    with tmp.open('xb') as f:
        f.write(canonical(obj)+b'\n'); f.flush(); os.fsync(f.fileno())
    try:
        # Atomic publication without overwriting another process's target.
        os.link(tmp,path)
    finally:
        tmp.unlink()


@contextmanager
def exclusive(run):
    """OS-owned lock releases on process death; never delete a possibly live lock."""
    run=Path(run); run.mkdir(parents=True,exist_ok=True)
    with (run/'execution.lock').open('a+b') as f:
        f.seek(0,2)
        if f.tell()==0: f.write(b'0'); f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try: yield
        finally:
            f.seek(0)
            if os.name=='nt': msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(f,fcntl.LOCK_UN)


def verify_package(package):
    package=Path(package).resolve()
    manifest=load(package/'MANIFEST.json')
    for rel,digest in manifest['files'].items():
        p=(package/rel).resolve()
        if not p.is_relative_to(package) or not p.is_file() or file_sha(p)!=digest:
            raise ValueError('Package integrity failure: '+rel)
    plan=load(package/'plan.json')
    validate(plan)
    if plan != build(package):
        raise ValueError('Plan differs from deterministic builder/materials')
    for c,specs in plan['payloads'].items():
        for m,spec in specs.items():
            if sha(spec)!=plan['payload_hashes'][c][m]: raise ValueError('Payload mismatch')
    return plan, file_sha(package/'MANIFEST.json')


def verify_launch(package, receipt):
    plan,digest=verify_package(package)
    r=load(receipt)
    required=('registration_reference','registered_utc','visibility','author_launch_instruction')
    if any(not isinstance(r.get(k),str) or not r[k].strip() for k in required):
        raise ValueError('Actual preregistration reference and author launch instruction required')
    if r.get('manifest_sha256')!=digest or r.get('visibility')!='public':
        raise ValueError('Receipt does not cover this publicly registered frozen package')
    if r.get('original_manifest_sha256')!=plan['amendment']['original_manifest_sha256']:
        raise ValueError('Amendment receipt does not link the original registered package')
    for field in ('registered_utc',):
        stamp=datetime.fromisoformat(r[field])
        if stamp.tzinfo is None or stamp>datetime.now(timezone.utc): raise ValueError('Invalid receipt timestamp')
    verify_jev_documentary_check(r,plan)
    environment=load(Path(package)/'ENVIRONMENT.json')
    import importlib.metadata
    import platform
    if not environment['python'].startswith(platform.python_version()+' '):
        raise ValueError('Python version differs from verified environment; document and reverify before launch')
    for name,version in environment['dependencies'].items():
        if importlib.metadata.version(name)!=version:
            raise ValueError('Dependency version changed: '+name+'; document and reverify before launch')
    # Frozen code must be the code actually imported, not a modified working copy.
    if Path(__file__).resolve().parent != (Path(package).resolve()/'code'):
        raise ValueError('Execute code/main_runner.py from the frozen package')
    return plan,digest,r


def verify_jev_documentary_check(receipt, plan, current=None):
    """Dated evidence is a documentary presumption, not a resolved snapshot identity."""
    current=current or datetime.now(timezone.utc)
    required=('jev_version_recheck_utc','jev_version_evidence','jev_presumed_model')
    if any(not isinstance(receipt.get(k),str) or not receipt[k].strip() for k in required):
        raise ValueError('Actual dated Jev documentary check required')
    stamp=datetime.fromisoformat(receipt['jev_version_recheck_utc'])
    if stamp.tzinfo is None or stamp>current or stamp.date()!=current.date():
        raise ValueError('Recheck Jev documentary identity on the launch/resume UTC date')
    if receipt['jev_presumed_model']!=plan['jev_presumed_version']:
        raise ValueError('Documentary presumption differs from frozen plan')
    return True


def attempt_dirs(run, slot):
    return sorted((Path(run)/'attempts'/slot).glob('*/request.json'))


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


def verify_run_lineage(plan,run,receipt):
    """Check the immutable pre-repair prefix and both registration chronologies."""
    run=Path(run);prefix=plan['amendment']['preserved_prefix']
    for rel,digest in prefix['files'].items():
        path=(run/rel).resolve()
        if not path.is_relative_to(run.resolve()) or not path.is_file() or file_sha(path)!=digest:
            raise ValueError('Preserved prefix changed or missing: '+rel)
    started=load(run/'started.json');original_receipt=load(run/'launch_record.json')
    if started['plan_sha256']!=plan['amendment']['original_plan_sha256']:
        raise ValueError('Original started plan does not match repair lineage')
    if original_receipt['manifest_sha256']!=plan['amendment']['original_manifest_sha256']:
        raise ValueError('Original launch receipt does not match repair lineage')
    if receipt.get('original_manifest_sha256')!=original_receipt['manifest_sha256']:
        raise ValueError('Amendment does not identify original manifest')
    original_time=datetime.fromisoformat(original_receipt['registered_utc'])
    amendment_time=datetime.fromisoformat(receipt['registered_utc'])
    if original_time.tzinfo is None or amendment_time.tzinfo is None or amendment_time<=original_time:
        raise ValueError('Invalid original/amendment registration chronology')
    rows={row['slot']:row for row in plan['schedule']}
    counts={}
    for path in run.glob('attempts/*/*/request.json'):
        rel=path.relative_to(run).as_posix();request=load(path);row=request['row']
        if row['slot'] not in rows or row!=rows[row['slot']]:
            raise ValueError('Request outside original schedule')
        if type(request.get('attempt')) is not int or request['attempt']<1 or rel!=f"attempts/{row['slot']}/{request['attempt']:02}/request.json":
            raise ValueError('Request path differs from its slot and attempt identity')
        expected=plan['payloads'][row['cell']][row['model']]
        if request.get('spec')!=expected or request.get('spec_sha256',sha(expected))!=sha(expected):
            raise ValueError('Request payload differs from the unchanged original payload')
        counts[row['slot']]=counts.get(row['slot'],0)+1
        stamp=datetime.fromisoformat(request['logged_before_dispatch_utc'])
        if stamp.tzinfo is None:raise ValueError('Request has no timezone')
        if rel in prefix['files']:
            if stamp<=original_time or stamp>=amendment_time:
                raise ValueError('Preserved attempt does not precede amendment and follow original registration')
        elif stamp<=amendment_time or request.get('amendment_manifest_sha256')!=receipt['manifest_sha256']:
            raise ValueError('New request missing prospective amendment authority')
    for slot,count in counts.items():
        if count>attempt_limit(plan,rows[slot]):raise ValueError('Repair attempt cap exceeded')
    for slot in prefix['already_obtained_slots']:
        if counts.get(slot)!=prefix['attempt_counts'][slot]:
            raise ValueError('Previously obtained slot was resent')
    return True


def unresolved_holds(run):
    run=Path(run);pending=[]
    for path in sorted((run/'global_holds').glob('*.json')):
        digest=file_sha(path);release=run/'hold_releases'/f'{digest}.json'
        if not release.exists():pending.append(path);continue
        record=load(release);hold=load(path)
        if record.get('hold_sha256')!=digest or any(not isinstance(record.get(k),str) or not record[k].strip() for k in ('author_instruction','evidence')):
            raise ValueError('Invalid persisted hold release')
        authorized=datetime.fromisoformat(record['authorized_utc'])
        if authorized.tzinfo is None or authorized<=datetime.fromisoformat(hold['timestamp_utc']):
            raise ValueError('Release must explicitly follow the held request')
    return pending


def record_hold_release(run,authorization,current):
    run=Path(run)
    required=('hold_sha256','authorized_utc','author_instruction','evidence')
    if any(not isinstance(authorization.get(key),str) or not authorization[key].strip() for key in required):
        raise ValueError('A separate explicit dated hold authorization and evidence are required')
    targets=[path for path in (run/'global_holds').glob('*.json') if file_sha(path)==authorization['hold_sha256']]
    if len(targets)!=1:raise ValueError('Authorization does not identify exactly one existing hold')
    when=datetime.fromisoformat(authorization['authorized_utc']);held=datetime.fromisoformat(load(targets[0])['timestamp_utc'])
    if when.tzinfo is None or not held<when<=datetime.fromisoformat(current):
        raise ValueError('Hold release authorization must be after hold and not in future')
    target=run/'hold_releases'/f"{authorization['hold_sha256']}.json"
    if target.exists():
        if load(target)!=authorization:raise ValueError('Cannot overwrite hold release')
    else:save(target,authorization)


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
                p=self.run/'suspensions'/f'{config}.json'
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
                    amendment_manifest_sha256=self.receipt['manifest_sha256'])
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
            if r.get('http_status')==429:
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
                if (self.run/'suspensions'/f'{m}.json').exists(): self.paused.add(m)
            # Reconstruct the whole history before any new inference, including crashes
            # after a response was saved but before its pause flag was persisted.
            for row in self.plan['schedule']:
                h=history(self.run,row,self.plan,recover=True)
                for r in h:
                    rel=f"attempts/{row['slot']}/{r['attempt']:02}/request.json"
                    if r.get('http_status')==429 and rel not in self.plan['amendment']['preserved_prefix']['files']:
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


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command',choices=['verify','execute'])
    cli.add_argument('--package',type=Path,required=True)
    cli.add_argument('--study-root',type=Path)
    cli.add_argument('--launch-record',type=Path)
    cli.add_argument('--resume-authorization',type=Path)
    a=cli.parse_args()
    if a.command=='verify':
        p,h=verify_package(a.package)
        print(json.dumps(dict(verified=True,slots=p['slots'],manifest_sha256=h,network_calls=0))); return
    if not a.study_root or not a.launch_record: cli.error('Execution needs study root and actual launch record')
    plan,digest,receipt=verify_launch(a.package,a.launch_record)
    run=a.study_root/'runs'/plan['run_id']
    # Main starts only under the explicit execute command after verification.
    def check(extra): return not compute(a.study_root,planned_eur=extra)['user_notice_required']
    run.mkdir(parents=True,exist_ok=True)
    # Immutable original receipt is checked inside the OS lock and is never replaced.
    authorization=load(a.resume_authorization) if a.resume_authorization else None
    save(run/'launch_checks'/(now().replace(':','-')+'-'+uuid.uuid4().hex+'.json'),receipt)
    print(json.dumps(Engine(plan,run,HttpTransport(),budget_check=check,amendment_receipt=receipt,
        resume_authorization=authorization).execute()))



if __name__=='__main__': main()
