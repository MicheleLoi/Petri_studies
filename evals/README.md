# evals

Raw `.eval` files produced by the Petri / Inspect-AI runner. **Ground truth, untampered — published verbatim.**

**428 `.eval` files** are present, across DE (German original + legacy compat), CH (Swiss), UK, and US. They include both confirmatory and **exploratory / in-progress** runs; the append-only [`../lab_journal.md`](../lab_journal.md) is the authoritative record of which is which, plus corrections and superseded entries.

## Layout

Flat per-polity directories — topic and condition are encoded in each filename, not in subdirectories:

```
evals/
├── de/   — German original + legacy-compat + multipolity runs (incl. _archive legacy)
├── uk/   — UK runs
└── us/   — US runs (EnSources / source-nationality arm)
```

Filename: `<ISO-timestamp>_<polity>-<topic>-<condition>_<id>.eval`
(e.g. `2026-06-15T14-53-25+02-00_us-ai-security-e1-c3_<id>.eval`).

## Provenance

Each `.eval` is an Inspect-AI log containing the full auditor/target/judge transcript, the model ratings, and the model-role identifiers. The run's stimulus (argument text, source identities, conditions) lives in `configs/<polity>/<topic>.yaml`; the runner commit is recoverable from git history. Analysis scripts are in `runner/` (`analyze_e1.py`, `analyze_stage0.py`).

> Note: a repo-wide `manifest.sha256` and a `--reproduce` byte-equivalence mode are described in earlier design docs but are **not yet implemented**; integrity currently rests on git history + the append-only lab journal.
