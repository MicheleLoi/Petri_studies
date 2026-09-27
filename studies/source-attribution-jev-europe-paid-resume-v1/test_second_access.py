import copy,json,unittest
from unittest.mock import patch
from pathlib import Path
import paid_runner as rr
from test_inherited import private_fixture
from test_repair import create_synthetic_prefix,Clock,Transport

class SecondAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=rr.load(Path(rr.original.__file__).resolve().parent.parent/'plan.json')
    def test_review_preserves_failed_attempt_and_raw_bytes(self):
        with private_fixture() as root:
            raw=dict(http_status=403,error_code='no_providers_available',rating_usable=False,rating=None,pause_model=True,status='pause')
            p=root/'result.json';rr.save(p,raw);before=p.read_bytes()
            policy=dict(rr.POLICY,reviewed_second_access_result='result.json',reviewed_second_access_result_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                view=rr.historical_view(root,p,raw)
                self.assertFalse(view['pause_model']);self.assertFalse(view['rating_usable']);self.assertIsNone(view['rating'])
                self.assertTrue(raw['pause_model']);self.assertEqual(before,p.read_bytes())
                p.write_text('{}')
                with self.assertRaises(ValueError):rr.historical_view(root,p,raw)
    def test_suspension_release_requires_exact_hash(self):
        with private_fixture() as root:
            p=root/'account_suspensions/jev.json';rr.save(p,{'reason':'access'})
            policy=dict(rr.POLICY,released_account_suspension='account_suspensions/jev.json',released_account_suspension_sha256=rr.file_sha(p))
            with patch.object(rr,'POLICY',policy):
                self.assertTrue(rr.released_account_suspension(root,'jev'))
                p.write_text('{}');self.assertFalse(rr.released_account_suspension(root,'jev'))
