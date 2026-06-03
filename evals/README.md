# evals

Raw `.eval` files produced by Petri. **Ground truth, untampered.** Published verbatim to GitHub.

> ⚠️ Phase A: empty (no evals generated yet — Petri integration deferred to Phase A2).

## Structure

```
evals/
├── manifest.sha256             — SHA-256 of every .eval file (integrity)
├── de/<topic>/<condition>/     — legacy compat (Phase B)
├── ch/<topic>/<condition>/
├── uk/<topic>/<condition>/
├── us/<topic>/<condition>/
└── it/<topic>/<condition>/
```

Each `.eval` filename uses the SID convention: `SID-YYYYMMDD-HHMMSS.eval`.

## Integrity protocol

After each push:

```bash
sha256sum evals/<polity>/<topic>/<condition>/*.eval > evals/manifest.sha256.tmp
sort evals/manifest.sha256.tmp -o evals/manifest.sha256
git add evals/manifest.sha256
git commit -m "evals: update manifest after <polity>/<topic> run (MOD-NNN)"
```

A revised pre-registration tag invalidates prior `.eval` files for the affected polity — they are NOT deleted (audit trail) but the README of the affected polity directory annotates them as `<filename>.eval (superseded by preregistered-<polity>-v2)`.

## Provenance embedded in each .eval

(Phase A2+) Each `.eval` will include a metadata block with:

- Runner commit SHA (this repo)
- Config file SHA-256
- Model snapshot identifier
- Timestamp (ISO-8601, UTC)
- Petri version (from `runner/requirements.lock`)
- Pre-registration tag (e.g., `preregistered-uk-v1`)

## Reproduction

```bash
python runner/petri_run.py --polity <polity> --topic <topic> --condition <id> --reproduce
```

Reads the existing `.eval`, re-runs Petri with the embedded provenance, asserts byte-equivalence on the SEED_INSTRUCTION + transcript hash.
