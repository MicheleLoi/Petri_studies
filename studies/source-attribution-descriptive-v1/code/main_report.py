"""Descriptive report only: no p-values, intervals, tests or imputation."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import statistics
from main_runner import history, save, exclusive, verify_package
from trace import file_sha, now, sha

PAIRS=(('I1','CP','CR'),('I2','CE','AEI'))


def describe(values):
    return dict(n=len(values),frequencies=[dict(value=k,count=v) for k,v in sorted(Counter(values).items())],
        mean=statistics.mean(values) if values else None,
        median=statistics.median(values) if values else None,
        minimum=min(values) if values else None,maximum=max(values) if values else None)


def contrasts(cells):
    rows=[]
    for name,left,right in PAIRS:
        delta={}
        for text in ('A','B'):
            a=cells[left+'_'+text]['mean']; b=cells[right+'_'+text]['mean']
            delta[text]=None if a is None or b is None else a-b
        interaction=None if None in delta.values() else delta['A']-delta['B']
        rows.append(dict(pair=name,left=left,right=right,contrast_A=delta['A'],contrast_B=delta['B'],
                         interaction=interaction,absolute_reference=.05,
                         relation_to_reference=None if interaction is None else
                         ('above' if abs(interaction)>.05+1e-12 else 'below' if abs(interaction)<.05-1e-12 else 'at')))
    return rows


def summarize(plan,run):
    run=Path(run); selected=[]; slots=[]; attempts=[]; files={}
    if not (run/'started.json').exists() or json.loads((run/'started.json').read_text())['plan_sha256']!=sha(plan):
        raise ValueError('Report plan does not match collection plan')
    for row in plan['schedule']:
        h=history(run,row,plan)
        usable=[r for r in h if r['rating_usable']]
        first=usable[0] if usable else None
        if first:
            selected.append(dict(**row,attempt=first['attempt'],rating=first['rating'],
                started_utc=first['started_utc'],finished_utc=first['finished_utc'],
                returned_model=first.get('returned_model'),presumed_model=first.get('presumed_model'),
                flags=first.get('flags',[]),response_text=first.get('response_text'),
                structured_answer=first.get('structured_answer'),pause_model=first['pause_model']))
        slots.append(dict(**row,attempts=len(h),obtained=bool(first),
            obtained_attempt=first['attempt'] if first else None,
            state='obtained' if first else 'exhausted' if len(h)==3 else 'paused' if
                (run/'suspensions'/f"{row['model']}.json").exists() or any(r['pause_model'] for r in h) else 'pending',
            problems=[dict(attempt=r['attempt'],category=r['category'],flags=r.get('flags',[])) for r in h if not r['rating_usable']]))
        for r in h:
            attempts.append(dict(slot=row['slot'],model=row['model'],cell=row['cell'],**r))
        for p in sorted((run/'attempts'/row['slot']).glob('*/*.json')):
            files[str(p.relative_to(run)).replace('\\','/')]=file_sha(p)
    models={}
    for m in plan['models']:
        rows=[r for r in selected if r['model']==m]
        status=[r for r in slots if r['model']==m]
        cells={}
        for c in plan['cells']:
            rs=[r for r in rows if r['cell']==c]; ss=[r for r in status if r['cell']==c]
            cells[c]=dict(**describe([r['rating'] for r in rs]),planned=len(ss),
                obtained_by_attempt={str(n):sum(r['attempt']==n for r in rs) for n in (1,2,3)},
                missing=len(ss)-len(rs),missing_states=dict(Counter(r['state'] for r in ss if not r['obtained'])),
                flagged_ratings=sum(bool(r['flags']) for r in rs),
                failed_attempt_categories=dict(Counter(a['category'] for a in attempts if a['model']==m and a['cell']==c and not a['rating_usable'])),
                problem_flags=dict(Counter(flag for a in attempts if a['model']==m and a['cell']==c for flag in a.get('flags',[]))))
        halves=[]
        for lo,hi in ((1,16),(17,32)):
            half={c:describe([r['rating'] for r in rows if r['cell']==c and lo<=r['block']<=hi]) for c in plan['cells']}
            halves.append(dict(blocks=[lo,hi],cells=half,contrasts=contrasts(half)))
        illustrations=[]
        for c in plan['cells']:
            rs=sorted((r for r in rows if r['cell']==c),key=lambda r:r['sequence'])
            illustrations.append(rs[0] if rs else dict(model=m,cell=c,missing=True))
        models[m]=dict(cells=cells,contrasts=contrasts(cells),halves=halves,illustrations=illustrations,
                       observed_versions=dict(Counter(str(r['returned_model']) for r in rows)))
    cost=sum(a['billing_estimate_usd']*plan['planning_eur_per_usd'] if a['billing_estimate_usd'] is not None
             else a['reserved_eur'] for a in attempts)
    return dict(schema='descriptive-report-v1',generated_utc=now(),models=models,selected_ratings=selected,
        slots=slots,attempts=attempts,planned=len(slots),obtained=len(selected),missing=len(slots)-len(selected),
        attempted_client_sends=len(attempts),technical_attempt_failures=sum(a['category']=='technical' for a in attempts),
        missing_rating_attempts=sum(a['category']=='missing_rating' and not a['rating_usable'] for a in attempts),
        flagged_obtained=sum(bool(r['flags']) for r in selected),
        unknown_cost_attempts=sum(a['billing_estimate_usd'] is None for a in attempts),
        planning_eur=cost,invoice_verified=False,source_hashes=files,
        complete=(run/'finished.json').exists(),synthetic=(run/'SYNTHETIC.json').exists(),
        warnings=['Descriptive observed ratings, not general population effects.',
                  'No p-values, confidence intervals, equivalence verdicts or independence claims.',
                  'Jev normalized rubric is a distinct measure; no direct magnitude ranking across models.',
                  'Version warnings retained; a suspended model requires review before interpreting completion.'])


def charts(summary,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    colors=plt.get_cmap('tab10').colors
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for ax,(m,result) in zip(axes.flat,summary['models'].items()):
        for y,(c,d) in enumerate(result['cells'].items()):
            for f in d['frequencies']:
                n=f['count']; offsets=[(i-(n-1)/2)*min(.018,.65/max(n,1)) for i in range(n)]
                ax.scatter([f['value']]*n,[y+v for v in offsets],s=14,marker='_',linewidths=.35,color=colors[y])
                ax.annotate('n='+str(n),(f['value'],y),xytext=(5,0),textcoords='offset points',fontsize=6,va='center')
        ax.set(yticks=range(8),yticklabels=list(result['cells']),xlim=(-.025,1.025),xlabel='Observed rating (Jev: score / 4)',title=m)
        ax.invert_yaxis(); ax.grid(axis='x',alpha=.2)
    fig.suptitle(('SYNTHETIC REHEARSAL — ' if summary['synthetic'] else '')+'Every obtained rating; stacked marks and counts show repetitions')
    for ext in ('png','pdf'): fig.savefig(out/f'ratings.{ext}',dpi=150)
    plt.close(fig)
    fig,axes=plt.subplots(4,1,figsize=(13,11),layout='constrained')
    for ax,(m,result) in zip(axes,summary['models'].items()):
        for i,c in enumerate(result['cells']):
            rows=[r for r in summary['selected_ratings'] if r['model']==m and r['cell']==c]
            ax.scatter([datetime.fromisoformat(r['started_utc']) for r in rows], [r['rating'] for r in rows],
                       label=c,s=13,alpha=.7,color=colors[i])
        ax.set(title=m,ylim=(-.025,1.025),ylabel='Rating',xlabel='Actual attempt start (UTC)')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
        ax.legend(ncol=8,fontsize=7,loc='upper center',bbox_to_anchor=(.5,1.03)); ax.grid(alpha=.2)
    fig.suptitle(('SYNTHETIC REHEARSAL — ' if summary['synthetic'] else '')+'Chronology of obtained ratings; no independence assumed')
    for ext in ('png','pdf'): fig.savefig(out/f'chronology.{ext}',dpi=150)
    plt.close(fig)


def fmt(x): return 'NA (empty required cell)' if x is None else f'{x:.6g}'


def render(plan,run,out,plots=True):
    run=Path(run); out=Path(out)
    with exclusive(run):
        summary=summarize(plan,run)
        out.mkdir(parents=True,exist_ok=False)
        save(out/'summary.json',summary)
        title='SYNTHETIC REHEARSAL — NOT STUDY DATA' if summary['synthetic'] else 'Descriptive source-attribution study'
        lines=['# '+title,'',f"Status: {'complete' if summary['complete'] else 'PARTIAL; collection unfinished or suspended'}.",
            f"Planned {summary['planned']}; obtained {summary['obtained']}; missing/pending {summary['missing']}; client attempts {summary['attempted_client_sends']}.",
            f"Technical failed/uncertain attempts {summary['technical_attempt_failures']}; unusable-rating attempts {summary['missing_rating_attempts']}; flagged obtained ratings {summary['flagged_obtained']}.",
            f"Planning cost EUR {summary['planning_eur']:.6f}; unknown-cost attempts {summary['unknown_cost_attempts']}; invoices not verified.",'',
            'Each cell uses all and only its first usable slot ratings. Missing cells are NA. Unequal counts do not cause deletion of other cells. All exact frequencies, attempt histories and file hashes are in summary.json.',
            'Reference 0.05 is descriptive and contestable. No p-values, confidence intervals or equivalence claims. Fixed planned halves are not independent replications. Jev uses a distinct rubric; its magnitudes must not be ranked directly against chat ratings.','']
        for m,r in summary['models'].items():
            lines += ['## '+m,'','Returned identities: '+json.dumps(r['observed_versions'])+'.','',
                '|Cell|Planned|Obtained|First / second / third|Missing|Mean|Median|Min–max|Flags|',
                '|---|---:|---:|---|---:|---:|---:|---|---:|']
            for c,d in r['cells'].items():
                ns=' / '.join(str(d['obtained_by_attempt'][str(n)]) for n in (1,2,3))
                lines.append(f"|{c}|{d['planned']}|{d['n']}|{ns}|{d['missing']}|{fmt(d['mean'])}|{fmt(d['median'])}|{fmt(d['minimum'])} – {fmt(d['maximum'])}|{d['flagged_ratings']}|")
            lines+=['','|Planned segment|Pair|Contrast on A|Contrast on B|Interaction|Relative to 0.05 (absolute)|','|---|---|---:|---:|---:|---|']
            for segment,cs in [('All',r['contrasts'])]+[(str(h['blocks']),h['contrasts']) for h in r['halves']]:
                for c in cs:
                    lines.append(f"|{segment}|{c['left']} − {c['right']}|{fmt(c['contrast_A'])}|{fmt(c['contrast_B'])}|{fmt(c['interaction'])}|{c['relation_to_reference'] or 'NA'}|")
            lines+=['']
            lines+=['|Cell|Unobtained slot states|Failed attempt categories|Flags across attempts|',
                    '|---|---|---|---|']
            for c,d in r['cells'].items():
                lines.append('|'+c+'|'+json.dumps(d['missing_states'])+'|'+json.dumps(d['failed_attempt_categories'])+'|'+json.dumps(d['problem_flags'])+'|')
            lines+=['']
        lines+=['## Plots','','![All ratings](ratings.png)','','![Chronology](chronology.png)','',
                '## Missingness and operational limits','',
                'Failures, missing scores and successful recoveries are retained by slot and by attempt in summary.json. The selected ratings can be affected by this acquisition procedure. Date/model changes and missing scores are not silently repaired.','',
                '## Illustrative responses','',
                'The first usable response in planned sequence for each cell appears in illustrations.json, with slot, attempt and version. These examples were not selected by effect size or rhetorical appeal. Other responses remain in the private raw archive.','']
        (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
        save(out/'illustrations.json',{m:r['illustrations'] for m,r in summary['models'].items()})
        if plots: charts(summary,out)
        save(out/'report_manifest.json',dict(generated_utc=now(),outputs={p.name:file_sha(p) for p in out.iterdir() if p.is_file()},
            raw_source_hashes=summary['source_hashes']))
    return summary


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--package',type=Path,required=True); cli.add_argument('--run',type=Path,required=True)
    cli.add_argument('--out',type=Path,required=True)
    args=cli.parse_args(); plan,_=verify_package(args.package)
    if Path(__file__).resolve().parent!=(args.package.resolve()/'code'): raise ValueError('Use frozen report code')
    s=render(plan,args.run,args.out)
    print(json.dumps({k:s[k] for k in ('planned','obtained','missing','synthetic','complete')}))
