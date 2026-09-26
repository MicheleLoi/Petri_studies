"""Prospective acquisition pacing; delegates collection to the frozen repair engine."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

BASE_MANIFEST = 'e5fdf0cf9147c29ef72776ece86a07abb3a516bf9f8e5686ba2f25e008b6a3a4'
INTERVAL = 60.0
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

class PacedTransport:
    """At least sixty seconds after each completed or failed transport call."""
    def __init__(self, inner, initial_wait=0, *, monotonic=time.monotonic, sleeper=time.sleep, log=lambda *a, **k: None):
        self.inner, self.clock, self.sleep, self.log = inner, monotonic, sleeper, log
        self.next_allowed = self.clock() + max(0, initial_wait)

    def prepare(self, model):
        remaining = self.next_allowed - self.clock()
        if remaining > 0:
            self.log('pacing_wait_started', minimum_interval_seconds=INTERVAL, remaining_seconds=remaining)
            while self.clock() < self.next_allowed:
                self.sleep(min(10, self.next_allowed - self.clock()))
            self.log('pacing_wait_completed', minimum_interval_seconds=INTERVAL)
        return self.inner.prepare(model)

    def send(self, spec, auth, timeout):
        try:
            return self.inner.send(spec, auth, timeout)
        finally:
            self.next_allowed = self.clock() + INTERVAL

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--base-package', type=Path, required=True)
    cli.add_argument('--study-root', type=Path, required=True)
    cli.add_argument('--launch-record', type=Path, required=True)
    cli.add_argument('--pacing-record', type=Path, required=True)
    cli.add_argument('--resume-authorization', type=Path, required=True)
    a = cli.parse_args()
    package = Path(__file__).resolve().parent
    manifest = load(package/'MANIFEST.json')
    for rel, expected in manifest['files'].items():
        path = (package/rel).resolve()
        assert path.is_relative_to(package) and digest(path) == expected, rel
    receipt = load(a.pacing_record)
    assert receipt['manifest_sha256'] == digest(package/'MANIFEST.json')
    assert receipt['visibility'] == 'public' and receipt['registration_reference']
    published = datetime.fromisoformat(receipt['registered_utc'])
    assert published.tzinfo is not None and published < datetime.now(timezone.utc)
    assert digest(a.base_package/'MANIFEST.json') == BASE_MANIFEST
    sys.path.insert(0, str(a.base_package/'code'))
    from main_runner import Engine, HttpTransport, verify_launch, verify_run_lineage, save, now, compute
    plan, _, original_receipt = verify_launch(a.base_package, a.launch_record)
    assert plan['parallel_workers'] == 1 and len(plan['worker_groups']) == 1
    run = a.study_root/'runs'/plan['run_id']
    verify_run_lineage(plan, run, original_receipt)
    for rel, expected in load(package/'PRESERVED_PREFIX.json')['files'].items():
        assert digest(run/rel) == expected, rel
    completed = [datetime.fromisoformat(load(p)['finished_utc']) for p in run.glob('attempts/*/*/result.json')]
    initial_wait = max(0, INTERVAL - (datetime.now(timezone.utc)-max(completed)).total_seconds()) if completed else 0
    transport = PacedTransport(HttpTransport(), initial_wait)
    engine = Engine(plan, run, transport,
        budget_check=lambda extra: not compute(a.study_root, planned_eur=extra)['user_notice_required'],
        amendment_receipt=original_receipt, resume_authorization=load(a.resume_authorization))
    transport.log = engine.log
    save(run/'pacing_launch_checks'/(now().replace(':','-')+'.json'), dict(
        pacing_receipt=receipt, base_manifest_sha256=BASE_MANIFEST,
        minimum_interval_seconds=INTERVAL, recorded_utc=now()))
    print(json.dumps(engine.execute()), flush=True)

if __name__ == '__main__': main()
