"""Synthetic offline tests for route admission, preservation and suspension."""
import copy,json,sys,unittest,uuid,shutil
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import route_runner as rr
import main_report
from test_repair import fixture,create_synthetic_prefix,Clock,Transport

@contextmanager
def private_fixture():
    parent=Path.cwd().resolve();root=parent/('synthetic-routing-'+uuid.uuid4().hex)
    root.mkdir()
    try:yield root
    finally:
        target=root.resolve()
        if target.parent!=parent or not target.name.startswith('synthetic-routing-'):raise ValueError('Unsafe fixture cleanup')
        shutil.rmtree(target)

class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=rr.load(Path(rr.original.__file__).resolve().parent.parent/'plan.json')
    def envelope(self,provider='digitalocean',count=1,model='typesafe-ai/jev'):
        e=fixture(self.plan);b=json.loads(e['body']);b['model']=model
        b['provider_metadata']['gateway']['routing'].update(finalProvider=provider,totalProviderAttemptCount=count)
        e['body']=json.dumps(b);return e
    def test_documented_route_accepted_without_claiming_snapshot(self):
        r=rr.assess('jev',self.envelope(),self.plan)
        self.assertTrue(r['identity_accepted']);self.assertFalse(r['pause_model']);self.assertFalse(r['version_verified'])
    def test_original_provider_retained(self):
        self.assertEqual(rr.assess('jev',self.envelope('typesafe-ai'),self.plan),rr.original.assess('jev',self.envelope('typesafe-ai'),self.plan))
    def test_unknown_provider_stops(self):self.assertTrue(rr.assess('jev',self.envelope('unknown'),self.plan)['pause_model'])
    def test_wrong_model_stops(self):self.assertTrue(rr.assess('jev',self.envelope(model='different'),self.plan)['pause_model'])
    def test_multiple_upstreams_stop(self):self.assertTrue(rr.assess('jev',self.envelope(count=2),self.plan)['pause_model'])
    def test_boolean_count_stops(self):self.assertTrue(rr.assess('jev',self.envelope(count=True),self.plan)['pause_model'])
    def test_rubric_error_not_masked(self):
        e=self.envelope();b=json.loads(e['body']);b['answers']['argument_strength']['legend']={};e['body']=json.dumps(b)
        self.assertTrue(rr.assess('jev',e,self.plan)['pause_model'])
    def test_429_remains_technical(self):
        r=rr.assess('jev',fixture(self.plan,429),self.plan)
        self.assertEqual(r['http_status'],429);self.assertFalse(r['rating_usable'])
    def test_hash_bound_historical_view_never_rewrites(self):
        with private_fixture() as t:
            root=Path(t);p=root/'result.json';raw=rr.original.assess('jev',self.envelope(),self.plan);rr.save(p,raw);before=p.read_bytes()
            policy=dict(rr.POLICY,accepted_historical_result='result.json',accepted_historical_result_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                reviewed=rr.historical_view(root,p,raw)
                self.assertTrue(reviewed['identity_accepted']);self.assertFalse(reviewed['pause_model']);self.assertEqual(p.read_bytes(),before)
                self.assertFalse(raw['identity_accepted'])
                p.write_text('{}')
                with self.assertRaises(ValueError):rr.historical_view(root,p,raw)
    def test_suspension_release_is_specific(self):
        with private_fixture() as t:
            root=Path(t);p=root/'suspensions/jev.json';rr.save(p,{'reason':'synthetic'})
            policy=dict(rr.POLICY,released_suspension_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                self.assertTrue(rr.released_suspension(root,'jev'))
                p.write_text('{}');self.assertFalse(rr.released_suspension(root,'jev'))
    def test_new_429_engine_stops_after_one_send(self):
        with private_fixture() as t:
            root=Path(t);run=root/'run';plan=copy.deepcopy(self.plan);create_synthetic_prefix(plan,run)
            rr.save(root/'MANIFEST.json',{'synthetic':True})
            receipt=dict(manifest_sha256='SYNTHETIC',registered_utc='2026-09-26T11:00:00+00:00',original_manifest_sha256=plan['amendment']['original_manifest_sha256'])
            clock=Clock();transport=Transport(plan,clock,lambda s,n:fixture(plan,429))
            policy=dict(rr.POLICY,accepted_historical_result='no-such-historical-result.json')
            with patch.object(rr,'PACKAGE',root),patch.object(rr,'POLICY',policy):
                e=rr.Engine(plan,run,transport,budget_check=lambda x:True,amendment_receipt=receipt,clock=clock.now,sleeper=clock.sleep)
                result=e.execute();self.assertEqual(len(transport.calls),1);self.assertTrue(result['global_hold']);self.assertFalse(result['complete'])
    def test_complete_synthetic_collection_and_original_descriptive_report(self):
        with private_fixture() as t:
            root=Path(t);run=root/'run';plan=copy.deepcopy(self.plan);create_synthetic_prefix(plan,run)
            rr.save(run/'SYNTHETIC.json',{'synthetic':True});rr.save(root/'MANIFEST.json',{'synthetic':True})
            receipt=dict(manifest_sha256='SYNTHETIC',registered_utc='2026-09-26T11:00:00+00:00',registration_reference='SYNTHETIC',original_manifest_sha256=plan['amendment']['original_manifest_sha256'])
            clock=Clock();transport=Transport(plan,clock,lambda s,n:self.envelope())
            paced=rr.PacedTransport(transport,monotonic=lambda:clock.value.timestamp(),sleeper=clock.sleep)
            policy=dict(rr.POLICY,accepted_historical_result='no-such-historical-result.json')
            with patch.object(rr,'PACKAGE',root),patch.object(rr,'POLICY',policy),patch.object(main_report,'history',rr.history):
                e=rr.Engine(plan,run,paced,budget_check=lambda x:True,amendment_receipt=receipt,clock=clock.now,sleeper=clock.sleep)
                result=e.execute();self.assertTrue(result['complete']);self.assertEqual(result['usable_slots'],288)
                self.assertEqual(len(transport.calls),286)
                summary=main_report.summarize(plan,run);self.assertEqual(summary['obtained'],288);self.assertEqual(summary['missing'],0)
                self.assertFalse(list((run/'route_suspensions').glob('*.json')))

if __name__=='__main__':unittest.main()
