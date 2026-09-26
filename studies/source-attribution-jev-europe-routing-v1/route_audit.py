"""Completion-only route/pacing audit. No means, contrasts or API calls."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime
import json
from pathlib import Path
import route_runner as rr

def check(value,message):
    if not value:raise ValueError(message)
def stamp(value):
    t=datetime.fromisoformat(value);check(t.tzinfo is not None,'Naive time');return t

def audit(study):
    run=study/'runs/registered-jev-europe-v1'
    check((run/'finished.json').exists(),'Collection has not finished; no analysis permitted')
    rr.verify_route_package();plan,base_digest=rr.verify_package(rr.BASE)
    route_receipt=rr.load(study/'jev-europe-routing-launch-record.json')
    pace_receipt=rr.load(study/'jev-europe-pacing-launch-record.json')
    check(route_receipt['manifest_sha256']==rr.file_sha(rr.PACKAGE/'MANIFEST.json'),'Route receipt mismatch')
    check(pace_receipt['manifest_sha256']==rr.POLICY['pacing_manifest_sha256'],'Pacing receipt mismatch')
    check(route_receipt['visibility']==pace_receipt['visibility']=='public','Missing public receipt')
    check(route_receipt['anonymous_access_verified'] and pace_receipt['anonymous_access_verified'],'Unverified deposit')
    prefix=rr.load(rr.PACKAGE/'PRESERVED_PREFIX.json')['files']
    pace_prefix=rr.load(rr.PACING/'PRESERVED_PREFIX.json')['files']
    repair_prefix=plan['amendment']['preserved_prefix']['files']
    with rr.exclusive(run):
        rr.verify_prefix(run)
        for rel,h in pace_prefix.items():check(rr.file_sha(run/rel)==h,'Pacing prefix changed')
        repair_receipt=rr.load(run/'amendment_launch_record.json')
        rr.verify_run_lineage(plan,run,repair_receipt)
        finished=rr.load(run/'finished.json')
        check(finished['complete'] and not finished['paused_models'] and not finished['budget_stopped'],'Not a completed run')
        check(not rr.unresolved_holds(run),'Unreleased HTTP429 hold')
        check(not list((run/'route_suspensions').glob('*.json')),'New suspension remains')
        for p in (run/'suspensions').glob('*.json'):check(rr.released_suspension(run,p.stem),'Unreleased old suspension')
        release=rr.load(run/'route_policy_release.json')
        check(release['policy']==rr.POLICY,'Wrong identity review')
        check(stamp(release['timestamp_utc'])>stamp(route_receipt['registered_utc']),'Review release precedes deposit')
        opened=sorted((rr.load(p) for p in (run/'operations').glob('*.json') if rr.load(p).get('kind')=='execution_opened'),key=lambda x:x['timestamp_utc'])
        times=[];providers=Counter();phases=Counter();raw_flags=Counter();obtained=0;hashes={};seen=set();by_invocation=defaultdict(list)
        for row in plan['schedule']:
            hs=rr.history(run,row,plan)
            check(1<=len(hs)<=rr.attempt_limit(plan,row),'Attempt limit/incomplete slot')
            selected=[i for i,r in enumerate(hs) if r['rating_usable']]
            check(selected==([len(hs)-1] if selected else []),'More than first usable response')
            check(selected or len(hs)==rr.attempt_limit(plan,row),'Unfinished missing slot')
            obtained+=bool(selected)
            for n,r in enumerate(hs,1):
                q=run/'attempts'/row['slot']/f'{n:02}'/'request.json';p=q.with_name('result.json');response=q.with_name('response.json')
                check(p.exists(),'Pending result');req=rr.load(q);raw=rr.load(p);rel=q.relative_to(run).as_posix();seen.add(rel)
                check(req['spec']==plan['payloads'][row['cell']]['jev'],'Payload changed')
                check(r['request_sha256']==rr.file_sha(q),'Request hash changed')
                phase='original' if rel in repair_prefix else 'repair' if rel in pace_prefix else 'paced' if rel in prefix else 'routing'
                phases[phase]+=1
                if response.exists():
                    reassess=rr.original.finish_result if rel in prefix else rr.finish_result
                    expected=reassess(req,q,rr.load(response),plan)
                    raw_copy=dict(raw);raw_copy.pop('recovered_from_saved_response',None)
                    check(raw_copy==expected,'Saved raw response does not reproduce under its original rule')
                    check(r['response_sha256']==rr.file_sha(response),'Response hash changed')
                else:
                    check(not r['rating_usable'] and r['category']=='technical' and r['billing_estimate_usd'] is None,'Invalid response-free result')
                check(not r['pause_model'],'Unresolved effective response flag')
                start,end=stamp(r['started_utc']),stamp(r['finished_utc'])
                check(start<=end<=stamp(finished['timestamp_utc']),'Invalid timing')
                if phase=='paced':check(start>stamp(pace_receipt['registered_utc']),'Paced request precedes deposit')
                if phase=='routing':
                    check(start>stamp(route_receipt['registered_utc']),'Route request precedes deposit')
                    check(req['route_manifest_sha256']==route_receipt['manifest_sha256'],'Wrong per-request route manifest')
                if n>1:check(start>=stamp(hs[n-2]['not_before_utc']),'Retry deadline bypassed')
                calls=[o for o in opened if stamp(o['timestamp_utc'])<=start];check(calls,'No execution event')
                by_invocation[calls[-1]['invocation']].append((start,row['sequence'],n))
                times.append((start,end,phase,q))
                if r['rating_usable']:
                    check(r['identity_accepted'] and r['legend_matches'],'Rating has unaccepted identity/rubric')
                    routing=r['gateway_metadata']['routing'];check(routing['finalProvider'] in rr.POLICY['allowed_providers'],'Unknown provider')
                    check(type(routing['totalProviderAttemptCount']) is int and routing['totalProviderAttemptCount']==1,'Multiple upstream calls')
                    check(r['returned_model'] in ('typesafe-ai/jev',plan['jev_presumed_version']),'Wrong model')
                    check(r['rating']==r['native_score']/4,'Normalization changed')
                    providers[routing['finalProvider']]+=1
                raw_flags.update(raw['flags'])
                for file in (q,p,response):
                    if file.exists():hashes[file.relative_to(run).as_posix()]=rr.file_sha(file)
        check(seen=={p.relative_to(run).as_posix() for p in run.glob('attempts/*/*/request.json')},'Orphan request')
        check(not list(run.rglob('*.writing')),'Incomplete writes')
        times.sort();gaps=[]
        for a,b in zip(times,times[1:]):
            check(a[1]<=b[0],'Overlapping calls')
            if b[2] in ('paced','routing'):
                gap=(b[0]-a[1]).total_seconds();check(gap>=60,'Pacing violated');gaps.append(gap)
        for entries in by_invocation.values():
            ordered=[(s,n) for t,s,n in sorted(entries)];check(ordered==sorted(ordered),'Sequence changed within invocation')
        for p in (run/'global_holds').glob('*.json'):
            held=rr.load(p);release=rr.load(run/'hold_releases'/f'{rr.file_sha(p)}.json')
            h,t=stamp(held['timestamp_utc']),stamp(release['authorized_utc'])
            check(h<t and not any(h<start<t for start,_,_,_ in times),'Calls during unreleased hold')
        check(finished['planned_slots']==finished['terminal_slots']==288 and finished['usable_slots']==obtained,'Finished counts mismatch')
    costs=rr.compute(study,planned_eur=0)
    return dict(verified=True,checked_utc=rr.now(),planned=288,obtained=obtained,missing=288-obtained,attempts=len(times),
        providers=dict(providers),attempts_by_phase=dict(phases),raw_historical_flags=dict(raw_flags),
        retrospective_review=rr.POLICY['accepted_historical_result'],minimum_paced_gap=min(gaps) if gaps else None,
        source_hashes=hashes,source_effects_analyzed=False,network_calls=0,
        cumulative_planning_eur=costs['planning_eur'],invoice_verified=False,
        note='Historical response reviewed after acquisition. Route equivalence and exact served snapshot are not established.')

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--study-root',type=Path,required=True);cli.add_argument('--out',type=Path,required=True)
    a=cli.parse_args();check(not a.out.exists(),'Audit output already exists');r=audit(a.study_root);rr.save(a.out,r)
    print(json.dumps({k:v for k,v in r.items() if k!='source_hashes'}))
