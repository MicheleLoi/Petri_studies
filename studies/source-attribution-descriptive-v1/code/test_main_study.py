"""Offline adversarial tests. Any accidental real HTTP send fails the suite."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import uuid
import threading
import unittest
from unittest.mock import patch
import requests
from main_plan import build
from main_adapters import assess, retry_wait, decode
from main_runner import Engine, save, exclusive, history
from main_report import summarize, describe, contrasts
from trace import sha, file_sha
from budget import compute

ROOT=Path(__file__).resolve().parent


def fixture(plan,model_key,rating=.5,**changes):
    model=model_key
    if model=='jev':
        score=rating*4; lo=int(score); hi=min(4,lo+1); p={str(n):0 for n in range(5)}
        p[str(lo)]+=hi-score if hi!=lo else 1
        if hi!=lo: p[str(hi)]+=score-lo
        q=plan['payloads'][plan['cells'][0]]['jev']['payload']['questions']['argument_strength']
        d=dict(model='typesafe-ai/jev',answers={'argument_strength':dict(type='score',score=score,confidence=.9,
            legend={str(i):c for i,c in enumerate(q['criteria'])},probabilities=p)},usage={'input_tokens':1,'output_tokens':1},
            provider_metadata={'gateway':{'cost':'0','routing':{'finalProvider':'typesafe-ai','totalProviderAttemptCount':1}}})
    else:
        text=json.dumps(dict(strength_rating=rating,strongest_point='SYNTHETIC',weakest_point='SYNTHETIC',overall_assessment='SYNTHETIC'))
        if model=='sonnet45': d=dict(model=plan['reference_models'][model],content=[dict(type='text',text=text)],stop_reason='end_turn',usage={'input_tokens':1,'output_tokens':1})
        elif model=='gpt4o': d=dict(model=plan['reference_models'][model],choices=[dict(message={'content':text},finish_reason='stop')],usage={'prompt_tokens':1,'completion_tokens':1})
        else: d=dict(modelVersion=plan['reference_models'][model],candidates=[dict(content={'parts':[{'text':text}]},finishReason='STOP')],usageMetadata={'promptTokenCount':1,'candidatesTokenCount':1})
    d.update(changes)
    return dict(http_status=200,body=json.dumps(d),headers={})


class FakeClock:
    def __init__(self): self.t=datetime(2026,9,24,18,0,tzinfo=timezone.utc); self.lock=threading.Lock()
    def now(self):
        with self.lock: return self.t.isoformat()
    def sleep(self,n):
        with self.lock: self.t+=timedelta(seconds=n)


class FakeTransport:
    def __init__(self,plan,clock,behavior=None): self.plan=plan; self.clock=clock; self.behavior=behavior; self.calls=[]; self.auth_calls=0
    def prepare(self,model): self.auth_calls+=1; return {}
    def send(self,spec,auth,timeout):
        self.calls.append(spec); self.clock.sleep(.1)
        return self.behavior(spec,len(self.calls)) if self.behavior else fixture(self.plan,spec['model_key'])


class MainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=build(ROOT) if (ROOT/'revisions').exists() else json.loads((ROOT.parent/'plan.json').read_text())
        cls.no_http=patch('requests.sessions.Session.send',side_effect=AssertionError('Network forbidden in offline tests'))
        cls.no_http.start()
    @classmethod
    def tearDownClass(cls): cls.no_http.stop()
    def setUp(self):
        self.tmp_root=(Path.cwd()/'tmp-main-tests').resolve(); self.tmp_root.mkdir(exist_ok=True)
        self.tmp=self.tmp_root/uuid.uuid4().hex; self.tmp.mkdir()
        self.run=self.tmp/'run'; self.p=copy.deepcopy(self.base)
        self.p['schedule']=self.p['schedule'][:1]; self.p['models']=['sonnet45']; self.p['blocks']=1
        self.clock=FakeClock()
    def tearDown(self):
        target=self.tmp.resolve()
        if target.parent!=self.tmp_root or not target.is_relative_to(Path.cwd().resolve()):
            raise ValueError('Unsafe test cleanup path')
        shutil.rmtree(target)
    def engine(self,behavior=None,budget=None):
        t=FakeTransport(self.p,self.clock,behavior)
        return Engine(self.p,self.run,t,budget_check=budget or (lambda x:True),clock=self.clock.now,sleeper=self.clock.sleep),t

    def test_full_schedule_and_approved_payloads(self):
        p=self.base
        self.assertEqual(len(p['schedule']),1024)
        for m in p['models']:
            for b in range(1,33):
                self.assertCountEqual([r['cell'] for r in p['schedule'] if r['model']==m and r['block']==b],p['cells'])
        for c in p['cells']:
            ss=p['payloads'][c]
            user=ss['gpt4o']['payload']['messages'][1]['content']
            self.assertEqual(user,ss['sonnet45']['payload']['messages'][0]['content'])
            self.assertEqual(user,ss['flash']['payload']['contents'][0]['parts'][0]['text'])
            self.assertEqual(user.split('\n\nPlease provide:')[0],ss['jev']['payload']['state'])
        self.assertNotIn('lite',p['models'])

    def test_all_provider_completion_and_usage(self):
        for m in self.base['models']:
            r=assess(m,fixture(self.base,m),self.base)
            self.assertTrue(r['rating_usable']); self.assertFalse(r['pause_model']); self.assertEqual(r['rating'],.5)
            self.assertIsNotNone(r['billing_estimate_usd'])

    def test_truncation_not_usable_even_valid_json(self):
        for m in self.base['models'][:-1]:
            e=fixture(self.base,m); d=json.loads(e['body'])
            if m=='sonnet45': d['stop_reason']='max_tokens'
            elif m=='gpt4o': d['choices'][0]['finish_reason']='length'
            else: d['candidates'][0]['finishReason']='MAX_TOKENS'
            e['body']=json.dumps(d)
            r=assess(m,e,self.base); self.assertFalse(r['rating_usable']); self.assertEqual(r['status'],'retry')

    def test_missing_changed_version_preserves_rating_but_pauses(self):
        for version in (None,'different'):
            r=assess('sonnet45',fixture(self.p,'sonnet45',model=version),self.p)
            self.assertTrue(r['rating_usable']); self.assertTrue(r['pause_model'])

    def test_duplicate_keys_and_multiple_json_rejected(self):
        with self.assertRaises(ValueError): decode('{"a":{"x":1,"x":2}}')
        with self.assertRaises(ValueError): decode('{}{}')
        with self.assertRaises(ValueError): decode('{"a":NaN}')

    def test_jev_auxiliary_anomaly_retains_score(self):
        e=fixture(self.base,'jev',rating=.9725); d=json.loads(e['body'])
        d['answers']['argument_strength']['probabilities']={'0':0,'1':.01,'2':.01,'3':.04,'4':.93}
        e['body']=json.dumps(d); r=assess('jev',e,self.base)
        self.assertTrue(r['rating_usable']); self.assertFalse(r['pause_model']); self.assertIsNone(r['score_distribution_consistent'])

    def test_jev_true_inconsistency_legend_and_fallback_pause(self):
        for change in ('probabilities','legend','provider','attempts'):
            e=fixture(self.base,'jev'); d=json.loads(e['body'])
            if change=='probabilities': d['answers']['argument_strength']['probabilities']={'0':1,'1':0,'2':0,'3':0,'4':0}
            elif change=='legend': d['answers']['argument_strength']['legend']={}
            elif change=='provider': d['provider_metadata']['gateway']['routing']['finalProvider']='other'
            else: d['provider_metadata']['gateway']['routing']['totalProviderAttemptCount']=2
            e['body']=json.dumps(d); self.assertTrue(assess('jev',e,self.base)['pause_model'])

    def test_http_classification_quota_not_retry(self):
        for code in (408,429,500,502,503,504,529):
            self.assertEqual(assess('gpt4o',dict(http_status=code,body='{}'),self.p)['status'],'retry')
        for code in (301,400,401,403,404,418):
            self.assertTrue(assess('gpt4o',dict(http_status=code,body='{}'),self.p)['pause_model'])
        self.assertTrue(assess('gpt4o',dict(http_status=429,body='{"error":{"code":"insufficient_quota"}}'),self.p)['pause_model'])

    def test_retry_after_seconds_date_invalid(self):
        self.assertEqual(retry_wait('12',2,self.clock.now()),(12,False))
        self.assertEqual(retry_wait('Thu, 24 Sep 2026 18:01:00 GMT',2,self.clock.now()),(60,False))
        self.assertEqual(retry_wait('nonsense',4,self.clock.now()),(4,True))

    def test_mixed_errors_share_three_attempts_then_first_usable(self):
        def behavior(spec,n):
            if n==1: raise requests.Timeout()
            if n==2: return fixture(self.p,'sonnet45',rating='bad')
            return fixture(self.p,'sonnet45',rating=.7)
        e,t=self.engine(behavior); result=e.execute()
        self.assertTrue(result['complete']); self.assertEqual(len(t.calls),3)
        s=summarize(self.p,self.run); self.assertEqual(s['selected_ratings'][0]['attempt'],3)
        self.assertEqual(s['unknown_cost_attempts'],1)
        e2,t2=self.engine(); e2.execute(); self.assertEqual(len(t2.calls),0)

    def test_three_failures_persist_across_resume(self):
        e,t=self.engine(lambda s,n:fixture(self.p,'sonnet45',rating=False)); e.execute()
        self.assertEqual(len(t.calls),3)
        e,t=self.engine(); e.execute(); self.assertEqual(len(t.calls),0)
        self.assertEqual(summarize(self.p,self.run)['missing'],1)

    def test_crash_reserved_attempt_never_resent(self):
        def crash(spec,n): raise RuntimeError('Synthetic crash after reservation')
        e,t=self.engine(crash)
        with self.assertRaises(RuntimeError): e.execute()
        path=next(self.run.glob('attempts/*/01/request.json')); before=file_sha(path)
        e,t=self.engine(); r=e.execute()
        self.assertTrue(r['complete']); self.assertEqual(len(t.calls),1); self.assertEqual(file_sha(path),before)
        s=summarize(self.p,self.run); self.assertEqual(s['selected_ratings'][0]['attempt'],2); self.assertEqual(s['unknown_cost_attempts'],1)

    def test_saved_response_recovery_without_send(self):
        e,t=self.engine(); row=self.p['schedule'][0]
        p=self.run/'attempts'/row['slot']/'01'/'request.json'
        save(p,dict(row=row,attempt=1,spec=self.p['payloads'][row['cell']][row['model']],logged_before_dispatch_utc=self.clock.now(),reserved_eur=.1))
        envelope=fixture(self.p,'sonnet45'); envelope['finished_utc']=self.clock.now(); save(p.with_name('response.json'),envelope)
        e.execute(); self.assertEqual(len(t.calls),0)
        self.assertTrue(json.loads(p.with_name('result.json').read_text())['recovered_from_saved_response'])

    def test_pause_survives_restart(self):
        self.p['schedule']=self.base['schedule'][:2]
        e,t=self.engine(lambda s,n:fixture(self.p,'sonnet45',model='changed')); r=e.execute()
        self.assertFalse(r['complete']); self.assertEqual(len(t.calls),1)
        e,t=self.engine(); e.execute(); self.assertEqual(len(t.calls),0)

    def test_saved_response_pause_detected_before_later_slots(self):
        self.p['schedule']=self.base['schedule'][:2]
        row=self.p['schedule'][0]; p=self.run/'attempts'/row['slot']/'01'/'request.json'
        save(p,dict(row=row,attempt=1,spec=self.p['payloads'][row['cell']][row['model']],logged_before_dispatch_utc=self.clock.now(),reserved_eur=.1))
        envelope=fixture(self.p,'sonnet45',model='different'); envelope['finished_utc']=self.clock.now()
        save(p.with_name('response.json'),envelope)
        e,t=self.engine(); r=e.execute()
        self.assertFalse(r['complete']); self.assertEqual(len(t.calls),0)
        self.assertIn('sonnet45',r['paused_models'])

    def test_no_rating_retry_delayed_and_exact_payload(self):
        e,t=self.engine(lambda s,n:fixture(self.p,'sonnet45',rating='bad' if n==1 else .6))
        e.execute(); self.assertEqual(len(t.calls),2); self.assertEqual(t.calls[0],t.calls[1])
        h=history(self.run,self.p['schedule'][0],self.p)
        self.assertGreaterEqual(datetime.fromisoformat(h[1]['started_utc']),datetime.fromisoformat(h[0]['not_before_utc']))

    def test_auth_failure_has_no_inference_attempt_and_persists(self):
        e,t=self.engine()
        t.prepare=lambda m:(_ for _ in ()).throw(ValueError('synthetic configuration issue'))
        r=e.execute(); self.assertEqual(len(t.calls),0); self.assertFalse(r['complete'])
        self.assertFalse(list(self.run.glob('attempts/**/request.json')))
        e,t=self.engine(); e.execute(); self.assertEqual(len(t.calls),0)

    def test_unequal_counts_empty_cell_and_illustrations(self):
        self.p['models']=['sonnet45']; self.p['blocks']=2
        self.p['schedule']=self.base['schedule'][:16]
        empty='CP_A'; specs=self.p['payloads']
        counter={}
        def behavior(spec,n):
            cell=next(c for c in self.p['cells'] if specs[c]['sonnet45']==spec)
            counter[cell]=counter.get(cell,0)+1
            rating=False if cell==empty else .25 if counter[cell]==1 else .75
            return fixture(self.p,'sonnet45',rating=rating)
        e,t=self.engine(behavior); e.execute(); s=summarize(self.p,self.run)
        r=s['models']['sonnet45']; self.assertEqual(r['cells'][empty]['n'],0)
        self.assertIsNone(r['contrasts'][0]['interaction']); self.assertIsNotNone(r['contrasts'][1]['interaction'])
        for item in r['illustrations']:
            if item['cell']!=empty: self.assertEqual(item['rating'],.25)

    def test_version_pause_does_not_stop_other_models(self):
        self.p['models']=list(self.base['models']); self.p['schedule']=[r for r in self.base['schedule'] if r['block']==1]
        def behavior(spec,n):
            m=spec['model_key']
            return fixture(self.p,m,**({'model':'changed'} if m=='sonnet45' else {}))
        e,t=self.engine(behavior); r=e.execute()
        self.assertFalse(r['complete']); self.assertEqual(sum(s['model_key']=='sonnet45' for s in t.calls),1)
        for m in ('gpt4o','flash','jev'): self.assertEqual(sum(s['model_key']==m for s in t.calls),8)

    def test_budget_stops_before_any_request(self):
        e,t=self.engine(budget=lambda n:False); r=e.execute()
        self.assertFalse(r['complete']); self.assertEqual(len(t.calls),0)
        self.assertFalse(list(self.run.glob('attempts/**/request.json')))

    def test_uncertain_attempt_cost_is_reserved_not_zero(self):
        root=self.tmp/'budget-root'; self.run=root/'runs'/'test'
        def crash(spec,n): raise RuntimeError('Synthetic uncertain dispatch')
        e,t=self.engine(crash)
        with self.assertRaises(RuntimeError): e.execute()
        b=compute(root)
        self.assertAlmostEqual(b['planning_eur'],.1)
        self.assertEqual(b['entries'][0]['status'],'reserve_unknown_cost')
        self.assertTrue(compute(root,planned_eur=99.9)['user_notice_required'])

    def test_mismatched_report_plan_is_rejected(self):
        e,t=self.engine(); e.execute()
        changed=copy.deepcopy(self.p); changed['delta']=.1
        with self.assertRaises(ValueError): summarize(changed,self.run)

    def test_second_live_runner_lock_rejected(self):
        with exclusive(self.run):
            with self.assertRaises((OSError,BlockingIOError)):
                with exclusive(self.run): pass

    def test_input_tampering_rejected_on_resume(self):
        e,t=self.engine(); e.execute()
        p=next(self.run.glob('attempts/*/01/request.json')); d=json.loads(p.read_text()); d['row']['cell']='bad'; p.write_text(json.dumps(d))
        with self.assertRaises(ValueError): history(self.run,self.p['schedule'][0],self.p)

    def test_hand_calculated_contrasts_unequal_counts(self):
        cells={c:describe([.5]) for c in self.base['cells']}
        cells.update(CP_A=describe([.8,.9,.7]),CR_A=describe([.6]),CP_B=describe([.7,.9]),CR_B=describe([.7,.7]))
        cs=contrasts(cells); self.assertAlmostEqual(cs[0]['contrast_A'],.2); self.assertAlmostEqual(cs[0]['contrast_B'],.1)
        self.assertAlmostEqual(cs[0]['interaction'],.1)
        cells['CP_A']=describe([]); cs=contrasts(cells)
        self.assertIsNone(cs[0]['interaction']); self.assertEqual(cs[1]['interaction'],0)

    def test_zero_constant_and_no_nan(self):
        d=describe([0,0,0]); self.assertEqual(d['mean'],0); self.assertEqual(d['frequencies'],[{'value':0,'count':3}])
        self.assertIsNone(describe([])['mean']); json.dumps(describe([]),allow_nan=False)

    def test_full_offline_run_and_halves(self):
        self.p=copy.deepcopy(self.base)
        e,t=self.engine(); r=e.execute(); self.assertTrue(r['complete']); self.assertEqual(len(t.calls),1024)
        s=summarize(self.p,self.run); self.assertEqual(s['obtained'],1024)
        for m,result in s['models'].items():
            for c,d in result['cells'].items(): self.assertEqual(d['n'],32)
            for h in result['halves']:
                for d in h['cells'].values(): self.assertEqual(d['n'],16)
            self.assertEqual(len(result['illustrations']),8)
            self.assertTrue(all(c['interaction']==0 for c in result['contrasts']))


if __name__=='__main__': unittest.main(verbosity=2)
