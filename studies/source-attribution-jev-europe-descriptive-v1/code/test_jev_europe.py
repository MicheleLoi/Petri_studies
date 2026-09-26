"""Offline adversarial tests; all real HTTP is forbidden."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import platform
import shutil
import threading
import unittest
from unittest.mock import patch
import uuid

from main_plan import build,validate,load
from main_runner import Engine,save,history,exclusive,verify_launch,verify_jev_documentary_check
from main_adapters import assess,retry_wait
from main_report import summarize,render
from budget import compute
from trace import sha,file_sha

PACKAGE=Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self):self.value=datetime(2026,9,26,12,tzinfo=timezone.utc);self.lock=threading.Lock()
    def now(self):
        with self.lock:return self.value.isoformat()
    def sleep(self,n):
        with self.lock:self.value+=timedelta(seconds=n)


def fixture(plan,model_key='jev',rating=.5,**changes):
    score=rating*4 if isinstance(rating,(int,float)) else rating
    probabilities={str(i):0. for i in range(5)}
    if isinstance(score,(int,float)) and 0<=score<=4:
        floor=int(score);probabilities[str(floor)]=1-(score-floor)
        if floor<4:probabilities[str(floor+1)]=score-floor
    criteria=plan['payloads'][plan['cells'][0]]['jev']['payload']['questions']['argument_strength']['criteria']
    answer=dict(type='score',score=score,confidence=.8,
                legend={str(i):v for i,v in enumerate(criteria)},probabilities=probabilities)
    body=dict(model='typesafe-ai/jev',answers={'argument_strength':answer},
        provider_metadata={'gateway':{'cost':'0.0001','routing':{'finalProvider':'typesafe-ai','totalProviderAttemptCount':1}}})
    body.update(changes)
    return dict(http_status=200,body=json.dumps(body),headers={})


def amend_answer(plan,**changes):
    envelope=fixture(plan);body=json.loads(envelope['body'])
    body['answers']['argument_strength'].update(changes);envelope['body']=json.dumps(body)
    return envelope


class Transport:
    def __init__(self,p,clock,behavior=None):self.p=p;self.clock=clock;self.behavior=behavior;self.calls=[]
    def prepare(self,m):return {}
    def send(self,spec,auth,timeout):
        self.calls.append(spec);self.clock.sleep(.01)
        return self.behavior(spec,len(self.calls)) if self.behavior else fixture(self.p)


class JevEuropeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=build(PACKAGE)
        cls.guard=patch('requests.sessions.Session.send',side_effect=AssertionError('Network forbidden'))
        cls.guard.start()
    @classmethod
    def tearDownClass(cls):cls.guard.stop()
    def setUp(self):
        self.temp_root=(Path.cwd()/'tmp-jev-europe-tests').resolve();self.temp_root.mkdir(exist_ok=True)
        self.directory=self.temp_root/uuid.uuid4().hex;self.directory.mkdir()
        self.run=self.directory/'runs/test';self.plan=copy.deepcopy(self.p);self.clock=Clock()
    def tearDown(self):
        target=self.directory.resolve()
        if target.parent!=self.temp_root or not target.is_relative_to(Path.cwd().resolve()):
            raise ValueError('Unsafe test cleanup path')
        shutil.rmtree(target)
    def small(self):
        self.plan['schedule']=self.plan['schedule'][:1];self.plan['blocks']=1
    def engine(self,behavior=None,budget=None):
        transport=Transport(self.plan,self.clock,behavior)
        return Engine(self.plan,self.run,transport,budget_check=budget or (lambda x:True),
                      clock=self.clock.now,sleeper=self.clock.sleep),transport
    def test_deterministic_balanced_288_slots(self):
        self.assertTrue(validate(self.p));self.assertEqual(build(PACKAGE),self.p)
        self.assertEqual(len(self.p['schedule']),288)
        self.assertEqual(len({r['cell'] for r in self.p['schedule']}),18)
        for block in range(1,17):
            rows=[r for r in self.p['schedule'] if r['block']==block]
            self.assertEqual(sum(r['cell'].startswith('DE_') for r in rows),10)
            self.assertEqual(sum(r['cell'].startswith('CH_') for r in rows),8)
        self.assertNotEqual([r['cell'] for r in self.p['schedule'][:18]],
                            [r['cell'] for r in self.p['schedule'][18:36]])
    def test_exact_original_criteria_and_frozen_extension_states(self):
        original=load(PACKAGE/'materials/JEV_SPEC_US.json')
        arguments=load(PACKAGE/'materials/ARGUMENTS.json')['arguments']
        historical=PACKAGE.parent/'extension-descriptive-v1/plan.json'
        if not historical.exists():historical=None
        historical_plan=load(historical) if historical else None
        for cell,specs in self.p['payloads'].items():
            case,source,part=cell.split('_');payload=specs['jev']['payload']
            q=payload['questions']['argument_strength']
            self.assertEqual(q['criteria'],original['question']['criteria'])
            self.assertEqual(q['type'],'score')
            self.assertEqual(q['instructions'],original['question']['instructions'].replace('about AI policy.',f"about {self.p['cases'][case]['topic']}."))
            self.assertIn(self.p['cases'][case]['organizations'][source],payload['state'])
            self.assertTrue(payload['state'].endswith('"'+arguments[case][part]['text']+'"'))
            if historical_plan:
                expected=historical_plan['payloads'][cell]['gpt4o']['payload']['messages'][1]['content'].split('\n\nPlease provide:')[0]
                self.assertEqual(payload['state'],expected)
    def test_native_score_and_usable_category(self):
        r=assess('jev',fixture(self.p,rating=.6075),self.p)
        self.assertTrue(r['rating_usable']);self.assertFalse(r['pause_model'])
        self.assertEqual(r['native_score'],2.43);self.assertEqual(r['rating'],.6075)
        self.assertEqual(r['category'],'usable');self.assertFalse(r['version_verified'])
    def test_probability_rounding_retained_without_renormalization(self):
        env=amend_answer(self.p,probabilities={'0':0.,'1':0.,'2':.99,'3':0.,'4':0.})
        r=assess('jev',env,self.p)
        self.assertTrue(r['rating_usable']);self.assertFalse(r['pause_model'])
        self.assertFalse(r['probabilities_valid']);self.assertIsNone(r['score_distribution_consistent'])
        self.assertEqual(r['structured_answer']['probabilities']['2'],.99)
    def test_valid_distribution_contradiction_pauses(self):
        r=assess('jev',amend_answer(self.p,score=3),self.p)
        self.assertTrue(r['rating_usable']);self.assertTrue(r['pause_model'])
        self.assertIn('score_distribution_inconsistent',r['flags'])
    def test_legend_mismatch_pauses(self):
        r=assess('jev',amend_answer(self.p,legend={'0':'changed'}),self.p)
        self.assertFalse(r['rating_usable']);self.assertTrue(r['pause_model'])
    def test_invalid_score_retries_and_auxiliary_metadata_does_not_filter(self):
        for score in (True,-1,5,'2',None):
            r=assess('jev',amend_answer(self.p,score=score),self.p)
            self.assertFalse(r['rating_usable']);self.assertFalse(r['pause_model'])
        r=assess('jev',amend_answer(self.p,confidence=None,extra='preserved'),self.p)
        self.assertTrue(r['rating_usable']);self.assertFalse(r['pause_model'])
        self.assertIn('additional_answer_fields',r['flags'])
    def test_duplicate_or_nonfinite_json_rejected(self):
        for body in ('{"model":"typesafe-ai/jev","model":"jev-1.13.0"}','{"model":NaN}'):
            r=assess('jev',dict(http_status=200,body=body),self.p)
            self.assertFalse(r['rating_usable']);self.assertTrue(r['pause_model'])
    def test_identity_and_routing_changed_pauses(self):
        r=assess('jev',fixture(self.p,model='other'),self.p)
        self.assertTrue(r['pause_model'])
        for routing in ({'finalProvider':'other','totalProviderAttemptCount':1},
                        {'finalProvider':'typesafe-ai','totalProviderAttemptCount':2}):
            r=assess('jev',fixture(self.p,provider_metadata={'gateway':{'routing':routing}}),self.p)
            self.assertTrue(r['pause_model'])
    def test_http_retry_and_permanent_billing_pause(self):
        r=assess('jev',dict(http_status=503,body='{}'),self.p)
        self.assertEqual(r['status'],'retry');self.assertFalse(r['pause_model'])
        r=assess('jev',dict(http_status=429,body='{"error":{"code":"insufficient_quota"}}'),self.p)
        self.assertTrue(r['pause_model'])
    def test_boolean_cost_or_attempt_count_is_not_numeric_metadata(self):
        gateway={'cost':True,'routing':{'finalProvider':'typesafe-ai','totalProviderAttemptCount':1}}
        r=assess('jev',fixture(self.p,provider_metadata={'gateway':gateway}),self.p)
        self.assertIsNone(r['billing_estimate_usd']);self.assertFalse(r['pause_model'])
        gateway['routing']['totalProviderAttemptCount']=True
        r=assess('jev',fixture(self.p,provider_metadata={'gateway':gateway}),self.p)
        self.assertTrue(r['pause_model'])
    def test_retry_after_minimum_and_invalid(self):
        self.assertEqual(retry_wait('7',2,self.clock.now()),(7,False))
        self.assertEqual(retry_wait('bad',4,self.clock.now()),(4,True))
        self.assertEqual(retry_wait('1',4,self.clock.now()),(4,False))
    def test_first_usable_not_repeated(self):
        self.small();e,t=self.engine();self.assertEqual(e.execute()['usable_slots'],1)
        e,t=self.engine();e.execute();self.assertEqual(t.calls,[])
    def test_three_attempt_limit_persists(self):
        self.small();e,t=self.engine(lambda s,n:amend_answer(self.plan,score=None))
        self.assertEqual(e.execute()['usable_slots'],0);self.assertEqual(len(t.calls),3)
        e,t=self.engine();e.execute();self.assertEqual(t.calls,[])
    def test_transient_recovery_keeps_exact_input_and_wait(self):
        self.small()
        def response(s,n):
            return dict(http_status=503,body='{}',headers={'Retry-After':'7'}) if n==1 else fixture(self.plan)
        e,t=self.engine(response);self.assertEqual(e.execute()['usable_slots'],1)
        self.assertEqual(t.calls[0],t.calls[1]);h=history(self.run,self.plan['schedule'][0],self.plan)
        self.assertGreaterEqual((datetime.fromisoformat(h[1]['started_utc'])-datetime.fromisoformat(h[0]['finished_utc'])).total_seconds(),7)
    def test_uncertain_attempt_never_resent(self):
        self.small()
        def crash(s,n):raise RuntimeError('Synthetic interrupted dispatch')
        e,t=self.engine(crash)
        with self.assertRaises(RuntimeError):e.execute()
        e,t=self.engine();self.assertEqual(e.execute()['usable_slots'],1);self.assertEqual(len(t.calls),1)
        h=history(self.run,self.plan['schedule'][0],self.plan)
        self.assertEqual(len(h),2);self.assertIn('uncertain_interrupted_attempt',h[0]['flags'])
        self.assertEqual(h[1]['attempt'],2)
    def test_saved_response_pause_recovered_before_new_send(self):
        self.small();e,t=self.engine(lambda s,n:fixture(self.plan,model='changed'))
        with patch('main_runner.finish_result',side_effect=RuntimeError('Synthetic post-response crash')):
            with self.assertRaises(RuntimeError):e.execute()
        e,t=self.engine();result=e.execute()
        self.assertEqual(t.calls,[]);self.assertEqual(result['paused_models'],['jev'])
    def test_suspension_survives_restart(self):
        self.small();e,t=self.engine(lambda s,n:fixture(self.plan,model='changed'))
        self.assertEqual(e.execute()['paused_models'],['jev'])
        e,t=self.engine();e.execute();self.assertEqual(t.calls,[])
    def test_budget_reserves_block_and_prevents_sends(self):
        e,t=self.engine(budget=lambda extra:False);r=e.execute()
        self.assertEqual(t.calls,[]);self.assertTrue(r['budget_stopped'])
        save(self.directory/'runs/unknown/01/request.json',dict(reserved_eur=.01,model_key='jev'))
        self.assertAlmostEqual(compute(self.directory)['planning_eur'],.01)
        self.assertTrue(compute(self.directory,planned_eur=99.99)['user_notice_required'])
    def test_historical_eu_premium_preserved(self):
        save(self.directory/'runs/old/01/request.json',dict(model_key='flash'))
        save(self.directory/'runs/old/01/result.json',dict(billing_estimate_usd=1))
        self.assertAlmostEqual(compute(self.directory)['planning_eur'],1.375)
    def test_os_lock_forbids_overlap_and_releases(self):
        with exclusive(self.run):
            with self.assertRaises(OSError):
                with exclusive(self.run):pass
        with exclusive(self.run):pass
    def test_request_and_response_hash_tampering_detected(self):
        self.small();e,t=self.engine();e.execute()
        p=next(self.run.glob('attempts/*/*/response.json'))
        p.write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Response hash mismatch'):
            history(self.run,self.plan['schedule'][0],self.plan)
    def test_daily_documentary_check_gate(self):
        current=datetime(2026,9,26,12,tzinfo=timezone.utc)
        r=dict(jev_version_recheck_utc='2026-09-26T10:12:36+00:00',
               jev_version_evidence='SYNTHETIC DOCUMENTARY EVIDENCE',jev_presumed_model='jev-1.13.0')
        self.assertTrue(verify_jev_documentary_check(r,self.p,current))
        for change in ({'jev_version_recheck_utc':'2026-09-25T10:00:00+00:00'},
                       {'jev_version_recheck_utc':'2026-09-26T13:00:00+00:00'},
                       {'jev_presumed_model':'other'},{'jev_version_evidence':''}):
            with self.assertRaises(ValueError):verify_jev_documentary_check({**r,**change},self.p,current)
    def test_publication_receipt_required_before_launch(self):
        stamp=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        receipt=dict(registration_reference='SYNTHETIC EXAMPLE',registered_utc=stamp,visibility='public',
            author_launch_instruction='SYNTHETIC AUTHORIZATION',manifest_sha256='digest',
            jev_version_recheck_utc=stamp,jev_version_evidence='SYNTHETIC EVIDENCE',jev_presumed_model='jev-1.13.0')
        env={'python':platform.python_version()+' TEST','dependencies':{}}
        def fake_load(path):return env if Path(path).name=='ENVIRONMENT.json' else receipt
        with patch('main_runner.verify_package',return_value=(self.p,'digest')),patch('main_runner.load',side_effect=fake_load):
            self.assertEqual(verify_launch(PACKAGE,'synthetic-receipt')[1],'digest')
            for key,value in (('visibility','private'),('registration_reference',''),('manifest_sha256','wrong')):
                before=receipt[key];receipt[key]=value
                with self.assertRaises(ValueError):verify_launch(PACKAGE,'synthetic-receipt')
                receipt[key]=before
    def test_full_report_known_interactions_missingness_and_halves(self):
        lookup={sha(spec):(cell,m) for cell,specs in self.plan['payloads'].items() for m,spec in specs.items()}
        def response(spec,n):
            cell,m=lookup[sha(spec)];_,source,part=cell.split('_')
            rating=.5+((.1 if part=='A' else -.1) if source in ('GJ','DIW','JG','SES') else 0)
            return fixture(self.plan,rating=rating)
        e,t=self.engine(response);result=e.execute()
        self.assertTrue(result['complete']);self.assertEqual(len(t.calls),288)
        save(self.run/'SYNTHETIC.json',{'synthetic':True})
        s=render(self.plan,self.run,self.directory/'report',plots=False)
        self.assertEqual(s['obtained'],288);self.assertEqual(len(s['models']),2)
        self.assertEqual(s['missing_rating_attempts'],0)
        for panel in s['models'].values():
            self.assertTrue(all(c['n']==16 for c in panel['cells'].values()))
            self.assertTrue(all(c['n']==8 for h in panel['halves'] for c in h['cells'].values()))
            self.assertEqual(panel['native_diagnostics']['probabilities_flagged'],0)
            for contrast in panel['contrasts']:
                self.assertAlmostEqual(contrast['interaction'],0 if contrast['left']=='DE_AFD' else .2)
        with self.assertRaises(FileExistsError):render(self.plan,self.run,self.directory/'report',plots=False)


if __name__=='__main__':unittest.main()
