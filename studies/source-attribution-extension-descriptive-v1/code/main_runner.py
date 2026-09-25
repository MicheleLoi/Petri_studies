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
from main_plan import load, build, validate
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
    for field in ('registered_utc',):
        stamp=datetime.fromisoformat(r[field])
        if stamp.tzinfo is None or stamp>datetime.now(timezone.utc): raise ValueError('Invalid receipt timestamp')
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


def attempt_dirs(run, slot):
    return sorted((Path(run)/'attempts'/slot).glob('*/request.json'))


def history(run, row, plan, recover=False):
    results=[]
    requests_found=attempt_dirs(run,row['slot'])
    if len(requests_found)>3: raise ValueError('Attempt budget exceeded on disk')
    for n,p in enumerate(requests_found,1):
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


class Engine:
    def __init__(self, plan, run, transport, *, budget_check, sleeper=time.sleep, clock=now):
        self.plan=plan; self.run=Path(run); self.transport=transport
        self.budget_check=budget_check; self.sleeper=sleeper; self.clock=clock
        self.mutex=threading.RLock(); self.stop=threading.Event()
        self.paused=set(); self.invocation=uuid.uuid4().hex

    def log(self, kind, **fields):
        with self.mutex:
            save(self.run/'operations'/f'{self.clock().replace(":","-")}-{uuid.uuid4().hex}.json',
                 dict(kind=kind,timestamp_utc=self.clock(),invocation=self.invocation,**fields))

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
        if any(r['rating_usable'] for r in h) or len(h)==3: return
        while len(h)<3 and m not in self.paused and not self.stop.is_set():
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
                    self.stop.set(); self.log('budget_notice_required',slot=row['slot']); return
                req=dict(row=row,attempt=n,spec=spec,spec_sha256=sha(spec),
                    logged_before_dispatch_utc=self.clock(),reserved_eur=reserve)
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
            if (self.run/'finished.json').exists(): return load(self.run/'finished.json')
            digest=sha(self.plan)
            if (self.run/'started.json').exists():
                if load(self.run/'started.json')['plan_sha256']!=digest: raise ValueError('Plan changed on resume')
            else: save(self.run/'started.json',dict(plan_sha256=digest,timestamp_utc=self.clock()))
            self.log('execution_opened',pid=os.getpid(),plan_sha256=digest)
            for m in self.plan['models']:
                if (self.run/'suspensions'/f'{m}.json').exists(): self.paused.add(m)
            # Reconstruct the whole history before any new inference, including crashes
            # after a response was saved but before its pause flag was persisted.
            for row in self.plan['schedule']:
                h=history(self.run,row,self.plan,recover=True)
                if any(r['pause_model'] for r in h) and row['model'] not in self.paused:
                    self.suspend(row['model'],'Persisted/recovered response requires review before resumption')
            with ThreadPoolExecutor(max_workers=self.plan['parallel_workers']) as pool:
                for block in range(1,self.plan['blocks']+1):
                    if self.stop.is_set(): break
                    rows=[r for r in self.plan['schedule'] if r['block']==block and r['model'] not in self.paused]
                    planned=0
                    for row in rows:
                        h=history(self.run,row,self.plan)
                        if not any(r['rating_usable'] for r in h): planned+=(3-len(h))*self.plan['reserve_eur_per_model'][row['model']]
                    if not self.budget_check(planned):
                        self.log('budget_notice_required',block=block,planned_batch_eur=planned); self.stop.set(); break
                    self.log('block_opened',block=block,planned_batch_reserve_eur=planned)
                    futures=[pool.submit(self.model_block,[r for r in rows if r['worker_group']==group]) for group in self.plan['worker_groups']]
                    for f in futures: f.result()
                    self.log('block_closed',block=block,paused_models=sorted(self.paused))
            terminal=0; usable=0
            for row in self.plan['schedule']:
                h=history(self.run,row,self.plan)
                has=any(r['rating_usable'] for r in h)
                terminal+=has or len(h)==3; usable+=has
            result=dict(timestamp_utc=self.clock(),planned_slots=len(self.plan['schedule']),terminal_slots=terminal,
                usable_slots=usable,paused_models=sorted(self.paused),budget_stopped=self.stop.is_set(),
                complete=terminal==len(self.plan['schedule']) and not self.paused)
            self.log('execution_closed',**{k:v for k,v in result.items() if k!='timestamp_utc'})
            if result['complete']: save(self.run/'finished.json',result)
            return result


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command',choices=['verify','execute'])
    cli.add_argument('--package',type=Path,required=True)
    cli.add_argument('--study-root',type=Path)
    cli.add_argument('--launch-record',type=Path)
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
    saved=run/'launch_record.json'
    if saved.exists():
        prior=load(saved)
        if prior['manifest_sha256']!=digest: raise ValueError('Run belongs to different package')
        if (run/'started.json').exists() and datetime.fromisoformat(prior['registered_utc'])>datetime.fromisoformat(load(run/'started.json')['timestamp_utc']):
            raise ValueError('Registration must precede first collection')
    else: save(saved,receipt)
    save(run/'launch_checks'/(now().replace(':','-')+'-'+uuid.uuid4().hex+'.json'),receipt)
    print(json.dumps(Engine(plan,run,HttpTransport(),budget_check=check).execute()))


if __name__=='__main__': main()
