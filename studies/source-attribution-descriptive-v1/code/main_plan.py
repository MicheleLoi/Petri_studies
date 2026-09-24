"""Build the adopted descriptive study without credentials or network access."""
import copy
import json
import random
from pathlib import Path
from trace import sha
from design import request_spec

MODELS = ('sonnet45', 'gpt4o', 'flash', 'jev')
CELLS = ('CR_A', 'CP_A', 'AEI_A', 'CE_A', 'CR_B', 'CP_B', 'AEI_B', 'CE_B')
REFERENCE = {'sonnet45': 'claude-sonnet-4-5-20250929', 'gpt4o': 'gpt-4o-2024-08-06',
             'flash': 'gemini-3.5-flash', 'jev': 'typesafe-ai/jev'}
RATES = {'sonnet45': [3, 15], 'gpt4o': [2.5, 10], 'flash': [1.5, 9]}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build(root):
    root = Path(root)
    prompt = load(root/'revisions/20260924-prompt-approved/PROMPT.json')
    jev = load(root/'jev_spec_v1.json')
    jev_cells = {c['cell']: c for c in load(root/'jev_inputs_v1.json')['cells']}
    payloads = {}
    for c in prompt['cells']:
        cell = c['cell']
        if sha(c['messages']) != c['messages_sha256']:
            raise ValueError('Approved prompt hash mismatch')
        payloads[cell] = {}
        for m in MODELS[:-1]:
            payloads[cell][m] = request_spec(m, smoke=False,
                system=c['messages'][0]['content'], user=c['messages'][1]['content'])
        p = copy.deepcopy(jev_cells[cell]['direct_typesafe_payload'])
        if sha(p) != jev_cells[cell]['payload_sha256']:
            raise ValueError('Jev original input hash mismatch')
        if p['state'] != c['messages'][1]['content'].split('\n\nPlease provide:')[0]:
            raise ValueError('Jev text/attribution differs from approved chat prompt')
        if p['questions']['argument_strength'] != jev['question']:
            raise ValueError('Jev rubric changed')
        p['model'] = REFERENCE['jev']
        payloads[cell]['jev'] = dict(model_key='jev', provider='vercel_typesafe',
            endpoint=jev['gateway_endpoint'], requested_model=REFERENCE['jev'], payload=p)
    schedule = []
    seeds = {'sonnet45': 2026092401, 'gpt4o': 2026092402, 'flash': 2026092403, 'jev': 20260924}
    historical_jev = load(root/'jev_schedule_v1.json')['slots']
    for m in MODELS:
        rng = random.Random(seeds[m])
        for block in range(1, 33):
            cells = list(CELLS)
            rng.shuffle(cells)
            for cell in cells:
                n = (block-1)*8 + cells.index(cell) + 1
                schedule.append(dict(slot=f'{m}-{n:04}', sequence=n, block=block, model=m, cell=cell))
    actual_jev = [{k: r[k] for k in ('slot', 'block', 'cell')} for r in schedule if r['model']=='jev']
    if actual_jev != historical_jev:
        raise ValueError('Prepared Jev order changed')
    return dict(schema='descriptive-study-v1', run_id='registered-study-v1', blocks=32,
        models=list(MODELS), cells=list(CELLS), slots=1024, schedule=schedule, seeds=seeds,
        schedule_rule='Explicit list authoritative; independent Python Random(seed) per model; shuffle eight cells per block.',
        payloads=payloads, payload_hashes={c: {m: sha(s) for m,s in specs.items()} for c,specs in payloads.items()},
        reference_models=REFERENCE, jev_presumed_version='jev-1.13.0',
        jev_version_source='https://docs.typesafe.ai/models', jev_version_checked_date='2026-09-24',
        parallel_workers=4, active_calls_per_model=1, global_block_barrier=True,
        scheduling='Four model workers per block; retries immediately within slot; all active workers finish block before next; no deliberate block pause.',
        maximum_client_attempts_per_slot=3, retry_delays_seconds=[2,4],
        timeout_connect_seconds=15, timeout_read_seconds=90, jev_timeout_read_seconds=60,
        retry_after='Honor longer Retry-After seconds or HTTP-date, including across restart; invalid header flagged.',
        transient_http=[408,429,500,502,503,504,529],
        nonretryable='Other HTTP errors, credential/config failures, explicit insufficient quota/billing: suspend model; no automatic release.',
        version_policy='Missing/different identity pauses model before further sends; retain score with version flag. Jev known alias allowed as presumed 1.13.0; require typesafe-ai routing.',
        unknown_dispatch='Persisted request never resent. Unfinished attempt counts and keeps reserve. Saved HTTP response is re-assessed offline; no response means uncertain attempt then next numbered attempt within limit.',
        suspension='Persistent result pause flag blocks subsequent model sends across restart. Other models continue. Releasing a pause requires a dated amendment; no CLI override.',
        rates_usd_per_million=RATES, rate_status='Historical planning rates, not invoice or guaranteed tariff; retain reserve if usage missing.',
        reserve_eur_per_attempt=.10, planning_eur_per_usd=1.25, alert_eur=100,
        budget_batch='Before each block reserve all remaining permitted sends in that block; recheck before each individual send under a shared lock.',
        analysis='All first usable ratings; pairwise CP-CR and CE-AEI; both interactions; cell frequencies/mean/median/min/max; fixed halves 1-16/17-32; chronology; no inference.',
        illustrative='First usable slot in planned model sequence within each cell; 24 verbatim chat responses and 8 structured Jev responses.',
        delta=.05, delta_status='Contestable descriptive reference only, not significance or equivalence',
        main_data_collected=False, registration_status='prepared_not_deposited')
