"""Prospective operational repair; the original scientific plan is unchanged."""
import copy
from pathlib import Path
from original_plan import build as original_build,validate as original_validate,load
from trace import sha,file_sha


def build(package):
    package=Path(package)
    original=original_build(package)
    frozen=load(package/'provenance/original-plan.json')
    prefix=load(package/'provenance/PRESERVED_PREFIX.json')
    if original!=frozen or sha(original)!=prefix['original_plan_sha256']:
        raise ValueError('Original scientific plan changed')
    if file_sha(package/'provenance/original-plan.json')!=prefix['original_plan_file_sha256']:
        raise ValueError('Original plan file changed')
    if file_sha(package/'provenance/original-manifest.json')!=prefix['original_manifest_sha256']:
        raise ValueError('Original manifest changed')
    plan=copy.deepcopy(original)
    plan['schema']='source-attribution-jev-europe-repair-v1'
    plan['amendment']=dict(id='jev-europe-repair-v1',preserved_prefix=prefix,
        original_plan_sha256=sha(original),original_manifest_sha256=prefix['original_manifest_sha256'],
        maximum_attempts_by_slot={row['slot']:(6 if row['slot'] in prefix['recoverable_slots'] else 3) for row in original['schedule']},
        added_attempts_per_recoverable_slot=3,
        global_hold_rule='Immediately stop the whole collector after any new HTTP 429; persist the hold across restart. Legacy 429s remain consumed but do not invoke the new rule retroactively.',
        resumption='A new HTTP 429 needs a separate dated author/operator authorization naming the exact hold hash. No automatic release, probe or routing change.',
        chronology='Preserve original publication and all 57 attempts. Every additional attempt must follow actual public amendment registration.',
        data_limitation='Operationally selected recovery of exhausted slots after provider-wide failures; actual collection is interrupted across phases. No new scientific cells, no replacement of prior scores.')
    plan['registration_status']='amendment_prepared_not_published'
    plan['scientific_data_collected']=True
    plan['amendment']['data_state_at_amendment']='57 attempts already exist, including two usable scores and 55 HTTP 429 responses; raw scores remain private. The amendment applies only prospectively.'
    validate(plan)
    return plan


def validate(plan):
    original_validate(plan)
    amendment=plan['amendment'];prefix=amendment['preserved_prefix']
    assert prefix['prefix_attempts']==57 and len(prefix['recoverable_slots'])==18
    assert len(prefix['already_obtained_slots'])==2
    assert len(set(prefix['recoverable_slots']))==18
    assert set(prefix['recoverable_slots']).isdisjoint(prefix['already_obtained_slots'])
    assert sum(prefix['attempt_counts'].values())==57
    assert all(prefix['attempt_counts'][slot]==3 for slot in prefix['recoverable_slots'])
    assert set(amendment['maximum_attempts_by_slot'])=={row['slot'] for row in plan['schedule']}
    for slot,cap in amendment['maximum_attempts_by_slot'].items():
        assert cap==(6 if slot in prefix['recoverable_slots'] else 3)
    assert len(prefix['files'])==173
    return True


def attempt_limit(plan,row):
    return plan['amendment']['maximum_attempts_by_slot'][row['slot']]
