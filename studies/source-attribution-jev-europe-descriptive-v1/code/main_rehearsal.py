"""Full offline synthetic rehearsal and descriptive report; forbids real HTTP."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from main_plan import build
from main_runner import Engine,save
from main_report import render
from test_jev_europe import Clock,Transport,fixture
from trace import now,sha


def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    plan=build(Path(__file__).resolve().parent.parent)
    run=out/'run';run.mkdir()
    save(run/'SYNTHETIC.json',dict(synthetic=True,created_utc=now()))
    clock=Clock();lookup={sha(spec):(cell,m) for cell,specs in plan['payloads'].items() for m,spec in specs.items()}
    def response(spec,n):
        cell,m=lookup[sha(spec)];_,source,part=cell.split('_')
        rating=.5+((.1 if part=='A' else -.1) if source in ('GJ','DIW','JG','SES') else 0)
        return fixture(plan,rating=rating)
    with patch('requests.sessions.Session.send',side_effect=AssertionError('Real HTTP forbidden')):
        transport=Transport(plan,clock,response)
        outcome=Engine(plan,run,transport,budget_check=lambda x:True,clock=clock.now,sleeper=clock.sleep).execute()
        report=render(plan,run,out/'report')
    assert outcome['complete'] and report['obtained']==288 and report['synthetic']
    assert len(report['models'])==2
    verification=dict(synthetic=True,real_api_calls=0,planned=288,obtained=288,panels=2,
        illustrations=sum(len(p['illustrations']) for p in report['models'].values()),
        checks=['full synthetic collection completed','DE and CH panels','16 scores per cell',
                '8 scores per cell in both halves','first usable structured illustrations',
                'descriptive report and ratings/chronology plots generated'])
    assert verification['illustrations']==18
    save(out/'verification.json',verification)
    print(json.dumps(verification))


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--out',type=Path,required=True)
    main(cli.parse_args().out)
