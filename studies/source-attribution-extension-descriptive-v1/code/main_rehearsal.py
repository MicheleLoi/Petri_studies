"""Full offline synthetic rehearsal and report; hard-blocks real HTTP."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from main_plan import build
from main_runner import Engine,save
from main_report import render
from test_extension import Clock,Transport,fixture
from trace import now,sha

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    plan=build(Path(__file__).resolve().parent.parent)
    run=out/'run';run.mkdir()
    save(run/'SYNTHETIC.json',dict(synthetic=True,created_utc=now()))
    clock=Clock();lookup={sha(spec):(cell,m) for cell,specs in plan['payloads'].items() for m,spec in specs.items()}
    def response(spec,n):
        cell,m=lookup[sha(spec)];_,source,part=cell.split('_')
        rating=.5+((.1 if part=='A' else -.1) if source in ('GJ','DIW','JG','SES','CP','CE') else 0)
        if m.endswith('_reasoning'):rating+=.03
        return fixture(plan,m,rating)
    with patch('requests.sessions.Session.send',side_effect=AssertionError('No real HTTP in rehearsal')):
        transport=Transport(plan,clock,response)
        outcome=Engine(plan,run,transport,budget_check=lambda x:True,clock=clock.now,sleeper=clock.sleep).execute()
        report=render(plan,run,out/'report')
    assert outcome['complete'] and report['obtained']==1664 and report['synthetic']
    assert len(report['models'])==12
    verification=dict(synthetic=True,real_api_calls=0,planned=1664,obtained=report['obtained'],
        panels=len(report['models']),illustrations=sum(len(p['illustrations']) for p in report['models'].values()),
        checks=['full collection completed','12 case/configuration panels','16 observations per eligible cell',
                '8 observations per cell in both halves','first usable illustrations','descriptive report and both plots generated'])
    assert verification['illustrations']==104
    save(out/'verification.json',verification)
    print(json.dumps(verification))

if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--out',type=Path,required=True)
    main(cli.parse_args().out)
