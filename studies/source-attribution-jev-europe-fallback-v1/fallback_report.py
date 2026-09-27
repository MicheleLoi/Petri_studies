"""Same descriptive computations, with explicit route review and disclosure."""
import argparse,json
from pathlib import Path
import fallback_runner as rr
import main_report as original

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--study-root',type=Path,required=True);cli.add_argument('--audit',type=Path,required=True);cli.add_argument('--out',type=Path,required=True)
    a=cli.parse_args();rr.verify_route_package();audit=rr.load(a.audit)
    if not audit['verified'] or audit['planned']!=288:raise ValueError('Completion audit required')
    run=a.study_root/'runs/registered-jev-europe-v1'
    if not (run/'finished.json').exists():raise ValueError('Collection not finished')
    rr.verify_prefix(run)
    for rel,h in audit['source_hashes'].items():
        if rr.file_sha(run/rel)!=h:raise ValueError('Data changed after audit')
    plan,_=rr.verify_package(rr.BASE)
    # The only data-view change is the hash-bound historical identity review.
    # All numerical calculations, cell definitions, contrasts and figures are original.
    original.history=rr.history
    summary=original.render(plan,run,a.out)
    note=('## Serving routes and retrospective eligibility review\n\n'
        'This collection includes Jev served through TypeSafe AI and/or DigitalOcean using the same Vercel account and unchanged payloads. '
        'Serving-route counts: '+json.dumps(audit['providers'])+'. Acquisition phases: '+json.dumps(audit['attempts_by_phase'])+'. '
        'Two already acquired responses were accepted in separate retrospective reviews: a DigitalOcean-served response and a later 503-to-200 failover response. '
        'Both original flags and suspensions remain preserved. The broadened provider rule was prospective only for subsequent requests. '
        'Neither review replaced or resent a response. Bounded failover admits at most two sequential attempts on the same Jev identifier, with one technical failure and one final success. No exact model snapshot or equivalence between serving routes is established. '
        'The alias remains a presumed version. Slower pacing and interruptions extend the observation period. '
        'Client calls are distinct from internal gateway attempts. Counts from available metadata: '+str(audit['reported_internal_attempts'])+' internal attempts across '+str(audit['requests_with_internal_metadata'])+' responses with routing metadata; '+str(audit['failed_internal_attempts'])+' recorded internal failures. The conservative extra reserve is EUR '+str(audit['upstream_uncertain_reserve_eur'])+'. Raw historical flags: '+json.dumps(audit['raw_historical_flags'])+'. See fallback_audit.json for immutable provenance and checks.\n\n')
    report=a.out/'REPORT.md';report.write_text(note+report.read_text(encoding='utf-8'),encoding='utf-8')
    rr.save(a.out/'fallback_audit.json',audit)
    manifest=a.out/'report_manifest.json';m=rr.load(manifest)
    m['outputs']={p.name:rr.file_sha(p) for p in a.out.iterdir() if p.is_file() and p.name!='report_manifest.json'}
    m['route_manifest_sha256']=rr.file_sha(rr.PACKAGE/'MANIFEST.json')
    manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('planned','obtained','missing','complete')}))
