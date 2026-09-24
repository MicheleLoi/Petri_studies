"""Derived cost view; reserves for missing usage are never silently zero."""
import json
from pathlib import Path
from trace import ROOT

FACTOR = 1.25  # Planning buffer in EUR per USD, not a measured exchange rate.
THRESHOLD = 100


def compute(root=ROOT, planned_eur=0):
    entries=[]
    # A request is logged before dispatch. Without a result, retain its reserve.
    for path in sorted(Path(root).glob('runs/**/request.json')):
        result_path=path.with_name('result.json')
        result=json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {}
        usd=result.get('billing_estimate_usd')
        eur=usd*FACTOR if usd is not None else result.get('reserved_eur',.10)
        entries.append(dict(request=str(path.relative_to(root)).replace('\\','/'),usd_estimate=usd,planning_eur=eur,
                            status='usage_estimate' if usd is not None else 'reserve_unknown_cost'))
    total=sum(e['planning_eur'] for e in entries)
    return dict(entries=entries,planning_eur=total,planned_next_eur=planned_eur,projected_eur=total+planned_eur,
                user_notice_required=total+planned_eur>=THRESHOLD,early_warning=total+planned_eur>=80,
                threshold_eur=THRESHOLD,factor=FACTOR,invoice_verified=False)


def render(root=ROOT):
    root=Path(root)
    result=compute(root)
    (root/'costs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=['# Costi API dello studio','',f"Conteggio prudenziale corrente: **{result['planning_eur']:.6f} euro**. Soglia richiesta dall'autore: **100 euro**; avviso anticipato operativo a 80.",
          '', 'Stime dai token dichiarati dal provider, con fattore prudenziale 1,25 euro per dollaro. Questo fattore include un margine di pianificazione: non è un tasso di cambio osservato né un calcolo fiscale. La fattura non è stata verificata. I tentativi senza usage mantengono una riserva invece di essere contati a zero.', '',
          '| Tentativo | Base | Euro di pianificazione |','|---|---|---:|']
    for e in result['entries']: rows.append(f"| [{e['request']}]({e['request']}) | {e['status']} | {e['planning_eur']:.6f} |")
    rows += ['', 'Ambito: richieste API registrate in questo banco di studio. Non include l’abbonamento Codex/Claude, attività di altri progetti o addebiti non osservati. Prima di ulteriori lotti il runner controlla il cumulato più la previsione del lotto: a 100 euro segnala la necessità di avvisare l’autore prima dell’invio. Non è un monitor della fatturazione del provider in background.', '']
    (root/'COSTI.md').write_text('\n'.join(rows),encoding='utf-8')
    return result


if __name__=='__main__': print(json.dumps(render(),ensure_ascii=False))
