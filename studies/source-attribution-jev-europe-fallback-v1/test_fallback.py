"""Offline tests for bounded failover and retained suspension/hold behavior."""
import copy,json,unittest
from unittest.mock import patch
from pathlib import Path
import fallback_runner as rr
from test_inherited import private_fixture
from test_repair import fixture,create_synthetic_prefix,Clock,Transport

class FallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=rr.load(Path(rr.original.__file__).resolve().parent.parent/'plan.json')
    def envelope(self,code=503):
        e=fixture(self.plan);b=json.loads(e['body'])
        a={'provider':'digitalocean','success':False,'statusCode':code,'startTime':100,'endTime':200}
        z={'provider':'typesafe-ai','success':True,'statusCode':200,'startTime':201,'endTime':300}
        b['provider_metadata']['gateway']['routing'].update(modelAttemptCount=1,totalProviderAttemptCount=2,
            modelAttempts=[{'canonicalSlug':'typesafe-ai/jev','success':True,'providerAttemptCount':2,'providerAttempts':[a,z]}])
        e['body']=json.dumps(b);return e
    def assess(self,e):return rr.assess('jev',e,self.plan)
    def mutate(self,change):
        e=self.envelope();b=json.loads(e['body']);change(b['provider_metadata']['gateway']['routing']);e['body']=json.dumps(b);return e
    def test_503_then_single_success_accepted(self):
        r=self.assess(self.envelope());self.assertFalse(r['pause_model']);self.assertTrue(r['identity_accepted']);self.assertFalse(r['version_verified'])
    def test_internal429_still_stops(self):
        r=self.assess(self.envelope(429));self.assertTrue(r['internal_http429']);self.assertTrue(r['pause_model'])
    def test_multiple_successes_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0]['providerAttempts'][0].update(success=True,statusCode=200)))['pause_model'])
    def test_unknown_provider_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0]['providerAttempts'][0].update(provider='unknown')))['pause_model'])
    def test_another_model_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0].update(canonicalSlug='other')))['pause_model'])
    def test_overlapping_attempts_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0]['providerAttempts'][1].update(startTime=150)))['pause_model'])
    def test_inconsistent_counts_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0].update(providerAttemptCount=1)))['pause_model'])
    def test_three_attempts_rejected(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r.update(totalProviderAttemptCount=3)))['pause_model'])
    def test_permanent_failure_rejected(self):self.assertTrue(self.assess(self.envelope(401))['pause_model'])
    def test_malformed_lists_rejected_without_crash(self):
        self.assertTrue(self.assess(self.mutate(lambda r:r['modelAttempts'][0].update(providerAttempts=None)))['pause_model'])
    def test_historical_fallback_review_is_hash_bound_and_nonmutating(self):
        with private_fixture() as root:
            p=root/'result.json';raw=rr.previous.assess('jev',self.envelope(),self.plan);rr.save(p,raw);before=p.read_bytes()
            policy=dict(rr.POLICY,accepted_fallback_result='result.json',accepted_fallback_result_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                reviewed=rr.historical_view(root,p,raw);self.assertFalse(reviewed['pause_model']);self.assertTrue(raw['pause_model']);self.assertEqual(p.read_bytes(),before)
                p.write_text('{}')
                with self.assertRaises(ValueError):rr.historical_view(root,p,raw)
    def test_internal429_engine_global_hold(self):
        with private_fixture() as root:
            run=root/'run';plan=copy.deepcopy(self.plan);create_synthetic_prefix(plan,run);rr.save(root/'MANIFEST.json',{'synthetic':True})
            receipt=dict(manifest_sha256='SYNTHETIC',registered_utc='2026-09-26T11:00:00+00:00',original_manifest_sha256=plan['amendment']['original_manifest_sha256'])
            clock=Clock();transport=Transport(plan,clock,lambda s,n:self.envelope(429))
            policy=dict(rr.POLICY,accepted_historical_result='no-old',accepted_fallback_result='no-new')
            with patch.object(rr,'PACKAGE',root),patch.object(rr,'POLICY',policy),patch.object(rr.previous,'POLICY',policy):
                e=rr.Engine(plan,run,transport,budget_check=lambda x:True,amendment_receipt=receipt,clock=clock.now,sleeper=clock.sleep)
                result=e.execute();self.assertTrue(result['global_hold']);self.assertEqual(len(transport.calls),1);self.assertFalse(result['complete'])

if __name__=='__main__':unittest.main()
