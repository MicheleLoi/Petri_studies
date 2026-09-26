"""Offline complete repair of a synthetic 57-attempt prefix; no real API or ratings."""
import argparse
import copy
import json
from pathlib import Path
from unittest.mock import patch
from main_plan import build
from main_runner import Engine,save
from main_report import render
from test_repair import Clock,Transport,create_synthetic_prefix
from trace import now


def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);run=out/'run'
    plan=copy.deepcopy(build(Path(__file__).resolve().parent.parent))
    create_synthetic_prefix(plan,run)
    save(run/'SYNTHETIC.json',dict(synthetic=True,note='All prefix and repaired responses are artificial fixtures. No real ratings copied.'))
    clock=Clock()
    receipt=dict(manifest_sha256='SYNTHETIC-REPAIR',registered_utc='2026-09-26T11:00:00+00:00',
        registration_reference='SYNTHETIC AMENDMENT',original_manifest_sha256=plan['amendment']['original_manifest_sha256'])
    with patch('requests.sessions.Session.send',side_effect=AssertionError('Real HTTP forbidden')):
        transport=Transport(plan,clock)
        result=Engine(plan,run,transport,budget_check=lambda x:True,amendment_receipt=receipt,
            clock=clock.now,sleeper=clock.sleep).execute()
        summary=render(plan,run,out/'report')
    assert result['complete'] and summary['obtained']==288 and summary['attempted_client_sends']==343
    assert summary['amendment']['attempts_by_phase']=={'original':57,'repair':286}
    verification=dict(synthetic=True,real_api_calls=0,original_synthetic_attempts=57,
        additional_synthetic_attempts=286,obtained_slots=288,preserved_prefix_verified=True,
        report_generated=True,panels=2,interactions=5)
    save(out/'verification.json',verification)
    print(json.dumps(verification))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    main(parser.parse_args().out)
