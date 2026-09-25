"""Offline deterministic builder for the author's descriptive extension."""
import copy
import json
from pathlib import Path
import random
from trace import sha

MODELS=['gpt4o','sonnet45','sol','sonnet5','sol_reasoning','sonnet5_reasoning']
REFERENCE={'gpt4o':'gpt-4o-2024-08-06','sonnet45':'claude-sonnet-4-5-20250929',
           'sol':'gpt-6-sol','sol_reasoning':'gpt-6-sol',
           'sonnet5':'claude-sonnet-5','sonnet5_reasoning':'claude-sonnet-5'}
GROUPS={'gpt4o':['gpt4o'],'sonnet45':['sonnet45'],
        'sol':['sol','sol_reasoning'],'sonnet5':['sonnet5','sonnet5_reasoning']}


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def request_spec(model,messages):
    thinking=model.endswith('_reasoning')
    cap=8192 if thinking else 1024
    openai=model in ('gpt4o','sol','sol_reasoning')
    if openai:
        payload=dict(model=REFERENCE[model],messages=copy.deepcopy(messages))
        if model=='gpt4o':payload.update(max_tokens=cap,temperature=1)
        else:
            payload.update(max_completion_tokens=cap,reasoning_effort='medium' if thinking else 'none')
            if not thinking:payload['temperature']=1
        endpoint='https://api.openai.com/v1/chat/completions'
    else:
        payload=dict(model=REFERENCE[model],system=messages[0]['content'],
                     messages=copy.deepcopy(messages[1:]),max_tokens=cap,
                     thinking={'type':'adaptive' if thinking else 'disabled'})
        if thinking:payload['output_config']={'effort':'high'}
        if model=='sonnet45':payload['temperature']=1
        endpoint='https://api.anthropic.com/v1/messages'
    return dict(model_key=model,provider='openai' if openai else 'anthropic',
                endpoint=endpoint,requested_model=REFERENCE[model],payload=payload)


def build(package):
    package=Path(package)
    cases=load(package/'materials/CASES.json')
    args=load(package/'materials/ARGUMENTS.json')['arguments']
    us=load(package/'materials/US_PROMPT.json')
    payloads={};cells=[];panels=[]
    us_cells={x['cell']:x for x in us['cells']}
    for case,definition in cases.items():
        case_cells=[]
        for part in ('A','B'):
            for source,organization in definition['organizations'].items():
                cell=f'{case}_{source}_{part}';cells.append(cell);case_cells.append(cell)
                if case=='US':
                    original=us_cells[f'{source}_{part}']
                    assert sha(original['messages'])==original['messages_sha256']
                    messages=copy.deepcopy(original['messages'])
                else:
                    template=us['user_template'].replace('about AI policy.',f"about {definition['topic']}.")
                    messages=[dict(role='system',content=us['system']),dict(role='user',
                        content=template.format(organization=organization,argument=args[case][part]['text']))]
                payloads[cell]={m:request_spec(m,messages) for m in definition['configs']}
        for m in definition['configs']:
            panels.append(dict(id=f'{case}_{m}',case=case,model=m,cells=case_cells,
                pairs=[[f'{case}_{a}',f'{case}_{b}'] for a,b in definition['pairs']]))
    seeds={m:2026092501+i for i,m in enumerate(GROUPS)}
    schedule=[]
    for group,configs in GROUPS.items():
        eligible=[(c,m) for c in cells for m in configs if m in payloads[c]]
        rng=random.Random(seeds[group]);sequence=0
        for block in range(1,17):
            shuffled=list(eligible);rng.shuffle(shuffled)
            for cell,model in shuffled:
                sequence+=1
                schedule.append(dict(slot=f'{group}-{sequence:04}',sequence=sequence,
                                     block=block,model=model,cell=cell,worker_group=group))
    p=dict(schema='source-attribution-extension-descriptive-v1',run_id='registered-extension-v1',
        blocks=16,models=MODELS,cells=cells,cases=cases,panels=panels,worker_groups=GROUPS,
        slots=1664,schedule=schedule,seeds=seeds,payloads=payloads,
        payload_hashes={c:{m:sha(s) for m,s in specs.items()} for c,specs in payloads.items()},
        reference_models=REFERENCE,provider_by_model={m:('openai' if m in ('gpt4o','sol','sol_reasoning') else 'anthropic') for m in MODELS},
        parallel_workers=4,active_calls_per_base_model=1,global_block_barrier=True,
        scheduling='Randomize all eligible case/cell/configuration slots within each base-model block; interleave reasoning off/on; barrier after every block; no deliberate pauses.',
        maximum_client_attempts_per_slot=3,retry_delays_seconds=[2,4],
        timeout_connect_seconds=15,timeout_read_seconds=90,reasoning_timeout_read_seconds=180,
        transient_http=[408,429,500,502,503,504,529],
        suspension='Persistent suspension propagates to both configurations of the base model. No automatic release or version substitution.',
        unknown_dispatch='An existing request is never resent as that attempt; preserve uncertain attempts and costs. Resume only next permitted numbered attempt.',
        rates_usd_per_million={m:([2.5,10] if m=='gpt4o' else [3,15] if m=='sonnet45' else [2,10]) for m in MODELS},
        reserve_eur_per_model={m:(.15 if m.endswith('_reasoning') else .04) for m in MODELS},
        planning_eur_per_usd=1.25,alert_eur=100,
        rate_status='2026-09-25 planning rates; conservative full-price usage, no cache discount; invoice unverified.',
        budget_batch='Include historical study and pilots, EU premium and explicit uncertain reserves; before each block include remaining permitted attempts; check again before each send.',
        halves=[[1,8],[9,16]],delta=.05,
        analysis='Descriptive only: all obtained first-usable slot ratings, every cell, all prespecified pair contrasts/interactions, halves, chronology and first planned usable illustration. No p-values, confidence intervals or equivalence verdicts.',
        configuration_comparisons=[dict(case='US',off='sol',on='sol_reasoning'),dict(case='US',off='sonnet5',on='sonnet5_reasoning')],
        history='Historical US study remains intact at 32 per cell, analyzed separately; no duplicate old-system US collection.',
        registration_status='prepared_not_published',scientific_data_collected=False)
    validate(p)
    return p


def validate(p):
    assert p['blocks']==16 and p['slots']==1664 and len(p['schedule'])==1664
    assert len({r['slot'] for r in p['schedule']})==1664
    assert len(p['panels'])==12
    for panel in p['panels']:
        rows=[r for r in p['schedule'] if r['model']==panel['model'] and r['cell'] in panel['cells']]
        assert len(rows)==len(panel['cells'])*16
        for block in range(1,17):
            assert sorted(r['cell'] for r in rows if r['block']==block)==sorted(panel['cells'])
    for row in p['schedule']:
        assert row['model'] in p['worker_groups'][row['worker_group']]
        spec=p['payloads'][row['cell']][row['model']]
        assert sha(spec)==p['payload_hashes'][row['cell']][row['model']]
    return True
