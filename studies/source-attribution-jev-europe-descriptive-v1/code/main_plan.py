"""Deterministic Jev supplement; only existing DE/CH topic texts and source labels."""
import copy
import hashlib
import json
from pathlib import Path
import random
from trace import sha

MODELS=['jev']
REFERENCE={'jev':'typesafe-ai/jev'}
GROUPS={'jev':['jev']}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build(package):
    package=Path(package)
    cases=load(package/'materials/CASES.json')
    arguments=load(package/'materials/ARGUMENTS.json')['arguments']
    template=load(package/'materials/STATE_TEMPLATE.json')['state_template']
    original=load(package/'materials/JEV_SPEC_US.json')
    payloads={}; cells=[]; panels=[]
    for case,definition in cases.items():
        case_cells=[]
        for part in ('A','B'):
            argument=arguments[case][part]
            if hashlib.sha256(argument['text'].encode('utf-8')).hexdigest()!=argument['text_sha256_utf8']:
                raise ValueError('Historical argument text hash mismatch')
            for source,organization in definition['organizations'].items():
                cell=f'{case}_{source}_{part}'; cells.append(cell); case_cells.append(cell)
                state=template.replace('about AI policy.',f"about {definition['topic']}.").format(
                    organization=organization,argument=argument['text'])
                question=copy.deepcopy(original['question'])
                question['instructions']=question['instructions'].replace('about AI policy.',f"about {definition['topic']}.")
                payload=dict(model=REFERENCE['jev'],state=state,questions={'argument_strength':question})
                payloads[cell]={'jev':dict(model_key='jev',provider='vercel_typesafe',
                    endpoint=original['gateway_endpoint'],requested_model=REFERENCE['jev'],payload=payload)}
        panels.append(dict(id=f'{case}_jev',case=case,model='jev',cells=case_cells,
            pairs=[[f'{case}_{a}',f'{case}_{b}'] for a,b in definition['pairs']]))
    seeds={'jev':2026092601};rng=random.Random(seeds['jev']);schedule=[]
    for block in range(1,17):
        shuffled=list(cells);rng.shuffle(shuffled)
        for cell in shuffled:
            n=len(schedule)+1
            schedule.append(dict(slot=f'jev-{n:04}',sequence=n,block=block,model='jev',cell=cell,worker_group='jev'))
    p=dict(schema='source-attribution-jev-europe-descriptive-v1',run_id='registered-jev-europe-v1',
        blocks=16,models=MODELS,cells=cells,cases=cases,panels=panels,worker_groups=GROUPS,
        slots=288,schedule=schedule,seeds=seeds,payloads=payloads,
        payload_hashes={c:{m:sha(s) for m,s in specs.items()} for c,specs in payloads.items()},
        reference_models=REFERENCE,provider_by_model={'jev':'vercel_typesafe'},
        jev_presumed_version='jev-1.13.0',jev_version_source='https://docs.typesafe.ai/models',
        version_policy='Accept typesafe-ai/jev as a presumed version, or explicit jev-1.13.0; require typesafe-ai routing and exactly one upstream attempt. Recheck documentary evidence on each launch/resume UTC date.',
        parallel_workers=1,active_calls_per_base_model=1,global_block_barrier=True,
        scheduling='Shuffle all 18 case/source/text cells independently within each of 16 blocks, interleaving DE/CH; one worker; no deliberate block pauses.',
        maximum_client_attempts_per_slot=3,retry_delays_seconds=[2,4],
        timeout_connect_seconds=15,timeout_read_seconds=60,reasoning_timeout_read_seconds=60,
        transient_http=[408,429,500,502,503,504,529],
        suspension='Persist every suspension; no automatic release, identity substitution or fallback.',
        unknown_dispatch='Existing request is never resent as that attempt. Preserve uncertain cost and consume attempt; only a next numbered permitted attempt may be sent.',
        rates_usd_per_million={},reserve_eur_per_model={'jev':.01},planning_eur_per_usd=1.25,alert_eur=100,
        rate_status='Use gateway reported cost when available, otherwise the stated per-attempt reserve; invoice unverified. No assumption of continued promotional free access.',
        budget_batch='Include all historical requests and Gemini EU premium. Before each block reserve all remaining permitted attempts; recheck before each send.',
        halves=[[1,8],[9,16]],delta=.05,
        analysis='Descriptive only: all first-usable slot scores divided by four; all cells and five planned interactions; fixed halves, chronology, native diagnostic distributions, and first planned usable structured answer per cell. No p-values, confidence intervals or equivalence verdicts.',
        configuration_comparisons=[],
        history='Prospective Jev supplement after viewing prior US Jev and DE/CH other-model results. Existing US Jev study remains intact at 32 per cell; new DE/CH use 16 per cell. No US re-collection.',
        comparability='Same Jev native rubric as US with topic substitution only; this rubric is not validated or calibrated to chat-model ratings. Cross-interface effect magnitudes do not isolate model differences.',
        registration_status='prepared_not_published',scientific_data_collected=False)
    validate(p)
    return p


def validate(p):
    assert p['blocks']==16 and p['slots']==288 and len(p['schedule'])==288
    assert p['models']==['jev'] and p['worker_groups']=={'jev':['jev']} and p['parallel_workers']==1
    assert len({r['slot'] for r in p['schedule']})==288 and len(p['cells'])==18
    assert [x['id'] for x in p['panels']]==['DE_jev','CH_jev']
    assert sum(len(x['pairs']) for x in p['panels'])==5
    assert p['maximum_client_attempts_per_slot']==3
    for block in range(1,17):
        assert sorted(r['cell'] for r in p['schedule'] if r['block']==block)==sorted(p['cells'])
    for n,row in enumerate(p['schedule'],1):
        assert row['sequence']==n and row['slot']==f'jev-{n:04}' and row['model']=='jev' and row['worker_group']=='jev'
        spec=p['payloads'][row['cell']]['jev']
        assert sha(spec)==p['payload_hashes'][row['cell']]['jev']
    return True
