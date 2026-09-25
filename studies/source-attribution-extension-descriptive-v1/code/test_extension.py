"""Offline adversarial checks; real HTTP is forbidden throughout this suite."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import shutil
import uuid
import threading
import unittest
from unittest.mock import patch

from main_plan import build,validate
from main_runner import Engine,save,history,exclusive
from main_adapters import assess
from main_report import summarize
from budget import compute
from trace import sha

PACKAGE=Path(__file__).resolve().parent.parent

class Clock:
    def __init__(self):self.value=datetime(2026,9,25,11,tzinfo=timezone.utc);self.lock=threading.Lock()
    def now(self):
        with self.lock:return self.value.isoformat()
    def sleep(self,n):
        with self.lock:self.value+=timedelta(seconds=n)

def fixture(plan,model_key,rating=.5,**changes):
    model=model_key
    text=json.dumps(dict(strength_rating=rating,strongest_point='SYNTHETIC',weakest_point='SYNTHETIC',overall_assessment='SYNTHETIC'))
    if plan['provider_by_model'][model]=='openai':
        body=dict(model=plan['reference_models'][model],choices=[dict(message={'content':text},finish_reason='stop')],
                  usage=dict(prompt_tokens=1,completion_tokens=1))
    else:
        body=dict(model=plan['reference_models'][model],content=[dict(type='thinking',thinking='SYNTHETIC'),dict(type='text',text=text)],
                  stop_reason='end_turn',usage=dict(input_tokens=1,output_tokens=1))
    body.update(changes)
    return dict(http_status=200,body=json.dumps(body),headers={})

class Transport:
    def __init__(self,p,clock,behavior=None):self.p=p;self.clock=clock;self.behavior=behavior;self.calls=[]
    def prepare(self,m):return {}
    def send(self,spec,auth,timeout):
        self.calls.append(spec);self.clock.sleep(.01)
        return self.behavior(spec,len(self.calls)) if self.behavior else fixture(self.p,spec['model_key'])

class ExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=build(PACKAGE)
        cls.guard=patch('requests.sessions.Session.send',side_effect=AssertionError('Network forbidden'))
        cls.guard.start()
    @classmethod
    def tearDownClass(cls):cls.guard.stop()
    def setUp(self):
        self.temp_root=(Path.cwd()/'tmp-extension-tests').resolve();self.temp_root.mkdir(exist_ok=True)
        self.directory=self.temp_root/uuid.uuid4().hex;self.directory.mkdir()
        self.run=self.directory/'runs/test'
        self.plan=copy.deepcopy(self.p);self.clock=Clock()
    def tearDown(self):
        target=self.directory.resolve()
        if target.parent!=self.temp_root or not target.is_relative_to(Path.cwd().resolve()):
            raise ValueError('Unsafe test cleanup path')
        shutil.rmtree(target)
    def small(self,models=('sol','sol_reasoning')):
        self.plan['schedule']=[next(r for r in self.p['schedule'] if r['model']==m) for m in models]
        self.plan['blocks']=1;self.plan['models']=list(models)
        self.plan['worker_groups']={g:[m for m in ms if m in models] for g,ms in self.p['worker_groups'].items() if any(m in models for m in ms)}
    def engine(self,behavior=None,budget=None):
        t=Transport(self.plan,self.clock,behavior)
        e=Engine(self.plan,self.run,t,budget_check=budget or (lambda x:True),clock=self.clock.now,sleeper=self.clock.sleep)
        return e,t
    def test_design_balance_and_exact_us_prompts(self):
        self.assertTrue(validate(self.p))
        historical=json.loads((PACKAGE/'materials/US_PROMPT.json').read_text(encoding='utf-8'))
        for cell in historical['cells']:
            for model in ('sol','sol_reasoning','sonnet5','sonnet5_reasoning'):
                pay=self.p['payloads']['US_'+cell['cell']][model]['payload']
                messages=pay['messages'] if model.startswith('sol') else [dict(role='system',content=pay['system'])]+pay['messages']
                self.assertEqual(messages,cell['messages'])
        for m in self.p['models']:
            payload=next(specs[m]['payload'] for specs in self.p['payloads'].values() if m in specs)
            self.assertEqual(payload.get('max_tokens',payload.get('max_completion_tokens')),8192 if m.endswith('_reasoning') else 1024)
        for g,configs in self.p['worker_groups'].items():
            if len(configs)>1:
                block=[r['model'] for r in self.p['schedule'] if r['worker_group']==g and r['block']==1]
                self.assertGreater(sum(a!=b for a,b in zip(block,block[1:])),2)
    def test_valid_all_configurations_and_truncation(self):
        for m in self.p['models']:
            r=assess(m,fixture(self.p,m),self.p)
            self.assertTrue(r['rating_usable']);self.assertFalse(r['pause_model'])
            env=fixture(self.p,m);body=json.loads(env['body'])
            if self.p['provider_by_model'][m]=='openai':body['choices'][0]['finish_reason']='length'
            else:body['stop_reason']='max_tokens'
            env['body']=json.dumps(body)
            self.assertFalse(assess(m,env,self.p)['rating_usable'])
    def test_first_usable_and_no_repeat(self):
        self.small();e,t=self.engine();result=e.execute()
        self.assertEqual(result['usable_slots'],2)
        e2,t2=self.engine();e2.execute();self.assertEqual(t2.calls,[])
    def test_three_attempt_limit_preserved_on_resume(self):
        self.small(('sol',));e,t=self.engine(lambda s,n:fixture(self.plan,s['model_key'],rating='not a rating'))
        result=e.execute();self.assertEqual(len(t.calls),3);self.assertEqual(result['usable_slots'],0)
        e2,t2=self.engine();e2.execute();self.assertEqual(t2.calls,[])
    def test_configuration_suspends_base_model(self):
        self.small();e,t=self.engine(lambda s,n:fixture(self.plan,s['model_key'],model='unexpected-model'))
        r=e.execute();self.assertEqual(len(t.calls),1)
        self.assertEqual(set(r['paused_models']),{'sol','sol_reasoning'})
        e2,t2=self.engine();e2.execute();self.assertEqual(t2.calls,[])
    def test_uncertain_attempt_never_resent(self):
        self.small(('sol',))
        def crash(s,n):raise RuntimeError('Synthetic interrupted dispatch')
        e,t=self.engine(crash)
        with self.assertRaises(RuntimeError):e.execute()
        e2,t2=self.engine();r=e2.execute();self.assertEqual(r['usable_slots'],1);self.assertEqual(len(t2.calls),1)
        h=history(self.run,self.plan['schedule'][0],self.plan)
        self.assertEqual(len(h),2);self.assertIn('uncertain_interrupted_attempt',h[0]['flags'])
        self.assertEqual(h[1]['attempt'],2)
    def test_saved_response_recovered_before_any_new_send(self):
        self.small();e,t=self.engine(lambda s,n:fixture(self.plan,s['model_key'],model='changed-model'))
        with patch('main_runner.finish_result',side_effect=RuntimeError('Synthetic failure after saved response')):
            with self.assertRaises(RuntimeError):e.execute()
        e2,t2=self.engine();r=e2.execute()
        self.assertEqual(t2.calls,[]);self.assertEqual(set(r['paused_models']),{'sol','sol_reasoning'})
    def test_budget_blocks_all_sends(self):
        self.small();e,t=self.engine(budget=lambda x:False);r=e.execute()
        self.assertEqual(t.calls,[]);self.assertTrue(r['budget_stopped'])
    def test_budget_preserves_explicit_uncertain_reserve(self):
        save(self.directory/'runs/reserve/01/request.json',dict(reserved_eur=.15,model_key='sol_reasoning'))
        self.assertAlmostEqual(compute(self.directory)['planning_eur'],.15)
        self.assertTrue(compute(self.directory,planned_eur=99.86)['user_notice_required'])
    def test_eu_premium_applies_to_historical_gemini_only(self):
        save(self.directory/'runs/old/01/request.json',dict(model_key='flash'))
        save(self.directory/'runs/old/01/result.json',dict(billing_estimate_usd=1))
        self.assertAlmostEqual(compute(self.directory)['planning_eur'],1.375)
    def test_os_lock_releases_and_forbids_overlap(self):
        with exclusive(self.run):
            with self.assertRaises(OSError):
                with exclusive(self.run):pass
        with exclusive(self.run):pass
    def test_report_known_interactions_and_halves(self):
        # Full schedule checks all 12 panels and all cells, not just one example.
        def response(spec,n):
            m=spec['model_key'];row=next(r for r in self.p['schedule'] if self.p['payloads'][r['cell']].get(m)==spec)
            _,source,part=row['cell'].split('_')
            rating=.5 + ((.1 if part=='A' else -.1) if source in ('GJ','DIW','JG','SES','CP','CE') else 0)
            if m.endswith('_reasoning'):rating+=.03
            return fixture(self.p,m,rating)
        e,t=self.engine(response);r=e.execute()
        self.assertTrue(r['complete']);self.assertEqual(len(t.calls),1664)
        s=summarize(self.plan,self.run)
        self.assertEqual(len(s['models']),12);self.assertEqual(s['obtained'],1664)
        for panel in s['models'].values():
            self.assertTrue(all(c['n']==16 for c in panel['cells'].values()))
            self.assertTrue(all(c['n']==8 for h in panel['halves'] for c in h['cells'].values()))
            for c in panel['contrasts']:
                self.assertAlmostEqual(c['interaction'],0. if c['left']=='DE_AFD' else .2)
        for comp in s['configuration_comparisons']:
            self.assertTrue(all(abs(d-.03)<1e-12 for d in comp['cell_mean_on_minus_off'].values()))
            self.assertTrue(all(abs(d['on_minus_off'])<1e-12 for d in comp['interactions']))

if __name__=='__main__':unittest.main()
