"""Repair-specific offline tests; all history fixtures are synthetic, never real ratings."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid
from main_plan import build,attempt_limit
from main_runner import Engine,save,history,finish_result,verify_run_lineage,record_hold_release
from main_report import summarize
from trace import sha,file_sha

PACKAGE=Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self):self.value=datetime(2026,9,26,12,tzinfo=timezone.utc)
    def now(self):return self.value.isoformat()
    def sleep(self,seconds):self.value+=timedelta(seconds=seconds)


def fixture(plan,status=200):
    if status!=200:return dict(http_status=status,body='{"error":{"type":"rate_limit_exceeded"}}',headers={})
    criteria=plan['payloads'][plan['cells'][0]]['jev']['payload']['questions']['argument_strength']['criteria']
    answer=dict(type='score',score=2.,confidence=.8,legend={str(i):v for i,v in enumerate(criteria)},
                probabilities={'0':0.,'1':0.,'2':1.,'3':0.,'4':0.})
    body=dict(model='typesafe-ai/jev',answers={'argument_strength':answer},
        provider_metadata={'gateway':{'cost':'0.0001','routing':{'finalProvider':'typesafe-ai','totalProviderAttemptCount':1}}})
    return dict(http_status=200,body=json.dumps(body),headers={})


class Transport:
    def __init__(self,plan,clock,behavior=None):self.plan=plan;self.clock=clock;self.behavior=behavior;self.calls=[]
    def prepare(self,model):return {}
    def send(self,spec,auth,timeout):
        self.calls.append(spec);self.clock.sleep(.01)
        return self.behavior(spec,len(self.calls)) if self.behavior else fixture(self.plan)


def create_synthetic_prefix(plan,run):
    """Same operational shape as the frozen prefix, without copying any real score."""
    prefix=plan['amendment']['preserved_prefix'];rows={r['slot']:r for r in plan['schedule']}
    save(run/'started.json',dict(plan_sha256=prefix['original_plan_sha256'],timestamp_utc='2026-09-26T10:25:00+00:00'))
    save(run/'launch_record.json',dict(manifest_sha256=prefix['original_manifest_sha256'],
        registered_utc=prefix['original_registered_utc'],registration_reference='SYNTHETIC ORIGINAL'))
    stamp=datetime(2026,9,26,10,30,tzinfo=timezone.utc)
    for slot,count in prefix['attempt_counts'].items():
        row=rows[slot]
        for attempt in range(1,count+1):
            stamp+=timedelta(seconds=1);path=run/'attempts'/slot/f'{attempt:02}'/'request.json'
            req=dict(row=row,attempt=attempt,spec=plan['payloads'][row['cell']]['jev'],
                logged_before_dispatch_utc=stamp.isoformat(),reserved_eur=.01)
            save(path,req)
            accepted=slot in prefix['already_obtained_slots'] and attempt==count
            envelope=fixture(plan,200 if accepted else 429)
            envelope['finished_utc']=(stamp+timedelta(microseconds=1000)).isoformat()
            save(path.with_name('response.json'),envelope)
            save(path.with_name('result.json'),finish_result(req,path,envelope,plan))
    prefix['files']={p.relative_to(run).as_posix():file_sha(p) for p in run.rglob('*.json')}
    assert len(prefix['files'])==173


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=build(PACKAGE)
        cls.guard=patch('requests.sessions.Session.send',side_effect=AssertionError('HTTP forbidden'))
        cls.guard.start()
    @classmethod
    def tearDownClass(cls):cls.guard.stop()
    def setUp(self):
        self.root=(Path.cwd()/'tmp-jev-repair-tests').resolve();self.root.mkdir(exist_ok=True)
        self.directory=self.root/uuid.uuid4().hex;self.run=self.directory/'run';self.run.mkdir(parents=True)
        self.plan=copy.deepcopy(self.base);self.clock=Clock();create_synthetic_prefix(self.plan,self.run)
        self.receipt=dict(manifest_sha256='SYNTHETIC-REPAIR',registered_utc='2026-09-26T11:00:00+00:00',
            registration_reference='SYNTHETIC AMENDMENT',original_manifest_sha256=self.plan['amendment']['original_manifest_sha256'])
    def tearDown(self):
        target=self.directory.resolve()
        if target.parent!=self.root or not target.is_relative_to(Path.cwd().resolve()):raise ValueError('Unsafe cleanup')
        shutil.rmtree(target)
    def engine(self,behavior=None,authorization=None):
        t=Transport(self.plan,self.clock,behavior)
        return Engine(self.plan,self.run,t,budget_check=lambda x:True,amendment_receipt=self.receipt,
            resume_authorization=authorization,clock=self.clock.now,sleeper=self.clock.sleep),t
    def test_only_selected_slots_gain_three_attempts_and_science_unchanged(self):
        original=json.loads((PACKAGE/'provenance/original-plan.json').read_text(encoding='utf-8'))
        for key in ('schedule','payloads','cells','panels','seeds','halves','cases'):
            self.assertEqual(self.plan[key],original[key])
        self.assertEqual(sum(attempt_limit(self.plan,r)==6 for r in self.plan['schedule']),18)
        self.assertEqual(sum(attempt_limit(self.plan,r)==3 for r in self.plan['schedule']),270)
    def test_complete_recovery_keeps_all57_and_no_repeat_of_two_successes(self):
        before=dict(self.plan['amendment']['preserved_prefix']['files'])
        e,t=self.engine();result=e.execute()
        self.assertTrue(result['complete']);self.assertEqual(result['usable_slots'],288)
        self.assertEqual(len(t.calls),286)
        for rel,digest in before.items():self.assertEqual(file_sha(self.run/rel),digest)
        summary=summarize(self.plan,self.run)
        self.assertEqual(summary['attempted_client_sends'],343)
        self.assertEqual(summary['amendment']['attempts_by_phase'],{'original':57,'repair':286})
        self.assertEqual(summary['amendment']['obtained_by_phase'],{'original':2,'repair':286})
        self.assertEqual(summary['obtained'],288)
        self.assertEqual(sum(x['obtained_attempt']==4 for x in summary['slots']),18)
        e,t=self.engine();e.execute();self.assertEqual(t.calls,[])
    def test_new429_stops_globally_before_another_slot_and_survives_restart(self):
        e,t=self.engine(lambda s,n:fixture(self.plan,429));result=e.execute()
        self.assertEqual(len(t.calls),1);self.assertTrue(result['global_hold']);self.assertFalse(result['budget_stopped'])
        self.assertEqual(len(list(self.run.glob('attempts/*/*/request.json'))),58)
        e,t=self.engine();result=e.execute();self.assertEqual(t.calls,[]);self.assertTrue(result['global_hold'])
    def test_saved429_response_recovers_global_hold_before_any_send(self):
        e,t=self.engine(lambda s,n:fixture(self.plan,429))
        with patch('main_runner.finish_result',side_effect=RuntimeError('Synthetic post-response crash')):
            with self.assertRaises(RuntimeError):e.execute()
        e,t=self.engine();result=e.execute()
        self.assertEqual(t.calls,[]);self.assertTrue(result['global_hold'])
    def test_explicit_dated_release_required_and_preserved(self):
        e,t=self.engine(lambda s,n:fixture(self.plan,429));e.execute()
        held=next(self.run.glob('global_holds/*.json'));digest=file_sha(held)
        self.clock.sleep(1)
        authorization=dict(hold_sha256=digest,authorized_utc=self.clock.now(),author_instruction='SYNTHETIC explicit resume',evidence='SYNTHETIC evidence')
        self.clock.sleep(1)
        wrong={**authorization,'authorized_utc':'2026-09-26T10:00:00+00:00'}
        with self.assertRaises(ValueError):record_hold_release(self.run,wrong,self.clock.now())
        e,t=self.engine(authorization=authorization);result=e.execute()
        self.assertTrue(result['complete']);self.assertTrue(held.exists())
        self.assertEqual(file_sha(held),digest)
        self.assertTrue((self.run/'hold_releases'/f'{digest}.json').exists())
    def test_attempt6_exhaustion_for_recovery_and_attempt3_elsewhere(self):
        # Stop the synthetic schedule after the first untouched slot; retain every prefix row.
        self.plan['schedule']=self.plan['schedule'][:21];self.plan['blocks']=2
        def bad(s,n):
            env=fixture(self.plan);body=json.loads(env['body']);body['answers']['argument_strength']['score']=None
            env['body']=json.dumps(body);return env
        e,t=self.engine(bad);result=e.execute()
        self.assertTrue(result['complete']);self.assertEqual(len(t.calls),57)
        for row in self.plan['schedule']:
            h=history(self.run,row,self.plan)
            if row['slot'] not in self.plan['amendment']['preserved_prefix']['already_obtained_slots']:
                self.assertEqual(len(h),attempt_limit(self.plan,row))
    def test_tampering_original_files_or_manifest_refuses_before_send(self):
        p=self.run/'attempts/jev-0002/01/result.json';p.write_text('{}',encoding='utf-8')
        e,t=self.engine()
        with self.assertRaisesRegex(ValueError,'Preserved prefix'):e.execute()
        self.assertEqual(t.calls,[])
    def test_wrong_lineage_receipt_rejected(self):
        self.receipt['original_manifest_sha256']='wrong'
        e,t=self.engine()
        with self.assertRaises(ValueError):e.execute()
        self.assertEqual(t.calls,[])
    def test_publication_after_new_attempt_is_rejected_before_dispatch(self):
        self.receipt['registered_utc']='2026-09-26T13:00:00+00:00'
        e,t=self.engine()
        with self.assertRaisesRegex(ValueError,'must follow amendment'):e.execute()
        self.assertEqual(t.calls,[])
        self.assertEqual(len(list(self.run.glob('attempts/*/*/request.json'))),57)
    def test_unregistered_extra_attempt_on_disk_is_rejected(self):
        row=next(r for r in self.plan['schedule'] if r['slot']=='jev-0002')
        save(self.run/'attempts/jev-0002/04/request.json',dict(row=row,attempt=4,
            spec=self.plan['payloads'][row['cell']]['jev'],logged_before_dispatch_utc='2026-09-26T10:59:59+00:00',
            reserved_eur=.01,amendment_manifest_sha256=self.receipt['manifest_sha256']))
        e,t=self.engine()
        with self.assertRaisesRegex(ValueError,'prospective amendment'):e.execute()
        self.assertEqual(t.calls,[])
    def test_orphan_request_path_is_rejected(self):
        row=next(r for r in self.plan['schedule'] if r['slot']=='jev-0002')
        save(self.run/'attempts/ORPHAN/04/request.json',dict(row=row,attempt=4,
            spec=self.plan['payloads'][row['cell']]['jev'],logged_before_dispatch_utc='2026-09-26T12:00:00+00:00',
            reserved_eur=.01,amendment_manifest_sha256=self.receipt['manifest_sha256']))
        e,t=self.engine()
        with self.assertRaisesRegex(ValueError,'Request path differs'):e.execute()
        self.assertEqual(t.calls,[])
    def test_future_usable_slot_cannot_be_resent(self):
        row=next(r for r in self.plan['schedule'] if r['slot']=='jev-0002')
        e,t=self.engine();e.slot(row)
        self.assertEqual(len(t.calls),1)
        save(self.run/'attempts/jev-0002/05/request.json',dict(row=row,attempt=5,
            spec=self.plan['payloads'][row['cell']]['jev'],logged_before_dispatch_utc=self.clock.now(),
            reserved_eur=.01,amendment_manifest_sha256=self.receipt['manifest_sha256']))
        with self.assertRaisesRegex(ValueError,'already usable'):history(self.run,row,self.plan)


if __name__=='__main__':unittest.main()
