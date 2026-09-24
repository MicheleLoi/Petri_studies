"""Full offline rehearsal with intentionally missing, delayed and constant data."""
import argparse
from collections import Counter
import json
from pathlib import Path
from unittest.mock import patch
import requests
from main_plan import build, load
from main_runner import Engine, save
from main_report import render
from test_main_study import FakeClock, FakeTransport, fixture


def rehearse(plan,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    run=out/'synthetic-run'; save(run/'SYNTHETIC.json',dict(synthetic=True,not_study_data=True,network_calls=0))
    counts=Counter(); clock=FakeClock()
    spec_to_cell={(m,json.dumps(s,sort_keys=True)):c for c,ss in plan['payloads'].items() for m,s in ss.items()}
    # Synthetic design: an entire missing CP_A cell for Sonnet; three unusable
    # ratings for each such slot, unequal recovery in flash, constant GPT, and
    # an auxiliary Jev probability anomaly that must not remove its score.
    def behavior(spec,n):
        m=spec['model_key']; c=spec_to_cell[(m,json.dumps(spec,sort_keys=True))]; counts[m,c]+=1
        source,text=c.split('_')
        rating={'CR':.4,'CP':.7,'AEI':.5,'CE':.6}[source] if text=='A' else {'CR':.5,'CP':.6,'AEI':.5,'CE':.7}[source]
        if m=='sonnet45' and c=='CP_A': return fixture(plan,m,rating=False)
        if m=='gpt4o': rating=.5
        if m=='flash' and c=='CR_B' and counts[m,c]%5==1: raise requests.Timeout()
        if m=='flash' and c=='AEI_B' and counts[m,c]<=3: return fixture(plan,m,rating='invalid')
        e=fixture(plan,m,rating=rating)
        if m=='jev' and c=='CP_A' and counts[m,c]==1:
            d=json.loads(e['body']); d['answers']['argument_strength']['probabilities']['0']+=.01
            e['body']=json.dumps(d)
        return e
    t=FakeTransport(plan,clock,behavior)
    with patch('requests.sessions.Session.send',side_effect=AssertionError('Offline rehearsal attempted real HTTP')):
        engine=Engine(plan,run,t,budget_check=lambda cost:True,sleeper=clock.sleep,clock=clock.now)
        result=engine.execute()
        before=len(t.calls)
        resumed=Engine(plan,run,t,budget_check=lambda cost:True,sleeper=clock.sleep,clock=clock.now).execute()
        if len(t.calls)!=before: raise AssertionError('Finished resume sent again')
        summary=render(plan,run,out/'report')
    if not result['complete'] or not resumed['complete']: raise AssertionError('Rehearsal not complete')
    if summary['obtained']!=991: raise AssertionError('Expected 1024 minus 32 empty-cell slots minus one flash slot')
    if summary['models']['sonnet45']['contrasts'][0]['interaction'] is not None: raise AssertionError('Empty cell not NA')
    if abs(summary['models']['jev']['contrasts'][0]['interaction']-.2)>1e-12: raise AssertionError('Known Jev contrast incorrect')
    if abs(summary['models']['jev']['contrasts'][1]['interaction']+.1)>1e-12: raise AssertionError('Known Jev contrast incorrect')
    if any(c['interaction']!=0 for c in summary['models']['gpt4o']['contrasts']): raise AssertionError('Constant data contrast incorrect')
    save(out/'verification.json',dict(network_calls=0,synthetic=True,planned=summary['planned'],obtained=summary['obtained'],
        attempts=len(t.calls),resume_additional_sends=0,checks=['empty cell NA','unequal counts','constant ratings',
            'timeout recovery','max three sends','Jev auxiliary flag','known I1=.2 and I2=-.1','finished resume sends zero']))
    return {k:summary[k] for k in ('planned','obtained','missing','attempted_client_sends','technical_attempt_failures')}


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__); cli.add_argument('--out',type=Path,required=True)
    cli.add_argument('--plan',type=Path); args=cli.parse_args()
    plan=load(args.plan) if args.plan else build(Path(__file__).resolve().parent)
    print(json.dumps(rehearse(plan,args.out)))
