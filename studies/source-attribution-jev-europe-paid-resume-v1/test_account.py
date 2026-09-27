import copy,json,unittest
from unittest.mock import patch
from pathlib import Path
import paid_runner as rr
from test_inherited import private_fixture
from test_repair import create_synthetic_prefix,Clock,Transport

class AccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=rr.load(Path(rr.original.__file__).resolve().parent.parent/'plan.json')
    def test_review_preserves_failed_attempt_and_raw_bytes(self):
        with private_fixture() as root:
            raw=dict(http_status=403,error_code='no_providers_available',rating_usable=False,rating=None,pause_model=True,status='pause')
            p=root/'result.json';rr.save(p,raw);before=p.read_bytes()
            policy=dict(rr.POLICY,reviewed_access_result='result.json',reviewed_access_result_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                view=rr.historical_view(root,p,raw)
                self.assertFalse(view['pause_model']);self.assertFalse(view['rating_usable']);self.assertIsNone(view['rating'])
                self.assertTrue(raw['pause_model']);self.assertEqual(before,p.read_bytes())
                p.write_text('{}')
                with self.assertRaises(ValueError):rr.historical_view(root,p,raw)
    def test_suspension_release_requires_exact_hash(self):
        with private_fixture() as root:
            p=root/'fallback_suspensions/jev.json';rr.save(p,{'reason':'access'})
            policy=dict(rr.POLICY,released_fallback_suspension='fallback_suspensions/jev.json',released_fallback_suspension_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                self.assertTrue(rr.released_fallback_suspension(root,'jev'))
                p.write_text('{}');self.assertFalse(rr.released_fallback_suspension(root,'jev'))
    def test_new403_still_stops_and_is_not_retried(self):
        with private_fixture() as root:
            run=root/'run';plan=copy.deepcopy(self.plan);create_synthetic_prefix(plan,run);rr.save(root/'MANIFEST.json',{'synthetic':True})
            receipt=dict(manifest_sha256='SYNTHETIC',registered_utc='2026-09-26T11:00:00+00:00',original_manifest_sha256=plan['amendment']['original_manifest_sha256'])
            clock=Clock()
            transport=Transport(plan,clock,lambda s,n:dict(http_status=403,body=json.dumps({'error':{'type':'no_providers_available','message':'Synthetic account restriction'}}),headers={}))
            policy=dict(rr.POLICY,accepted_historical_result='no-old',accepted_fallback_result='no-fallback',reviewed_access_result='no-access')
            with patch.object(rr,'PACKAGE',root),patch.object(rr,'POLICY',policy),patch.object(rr.previous,'POLICY',policy):
                engine=rr.Engine(plan,run,transport,budget_check=lambda x:True,amendment_receipt=receipt,clock=clock.now,sleeper=clock.sleep)
                result=engine.execute()
                self.assertEqual(len(transport.calls),1);self.assertEqual(result['paused_models'],['jev']);self.assertFalse(result['complete'])
                self.assertTrue((run/'paid_suspensions/jev.json').exists())

if __name__=='__main__':unittest.main()
