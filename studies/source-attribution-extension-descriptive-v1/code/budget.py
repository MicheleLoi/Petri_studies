"""Parallel cumulative ledger: preserve historical files; honor explicit reserves and EU premium."""
import json
from pathlib import Path
FACTOR=1.25

def compute(root,planned_eur=0):
    entries=[]
    for p in sorted(Path(root).glob('runs/**/request.json')):
        req=json.loads(p.read_text(encoding='utf-8'))
        rp=p.with_name('result.json')
        r=json.loads(rp.read_text(encoding='utf-8')) if rp.exists() else {}
        usd=r.get('billing_estimate_usd')
        reserve=max(req.get('reserved_eur',.10),r.get('reserved_eur',req.get('reserved_eur',.10)))
        model=req.get('row',{}).get('model') or req.get('model_key') or req.get('model') or req.get('spec',{}).get('model_key')
        if isinstance(model,dict):model=model.get('model_key') or model.get('id')
        premium=1.1 if isinstance(model,str) and (model in ('flash','lite') or model.startswith('gemini-')) else 1.
        euro=usd*FACTOR*premium if usd is not None else reserve
        entries.append(dict(request=str(p.relative_to(root)).replace('\\','/'),planning_eur=euro,
                            usd_estimate=usd,status='usage_estimate' if usd is not None else 'reserve_unknown_cost'))
    total=sum(e['planning_eur'] for e in entries)
    return dict(entries=entries,planning_eur=total,planned_next_eur=planned_eur,projected_eur=total+planned_eur,
                user_notice_required=total+planned_eur>=100,early_warning=total+planned_eur>=80,
                threshold_eur=100,factor=FACTOR,invoice_verified=False)
