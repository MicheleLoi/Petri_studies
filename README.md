# source-attribution-bias-multipolity

**Multi-polity replication of the source-attribution-bias study** (Anthropic Petri framework / Inspect-AI), extending the German (DE) and Swiss (CH) iterations to the United Kingdom (UK), United States (US), and Italy (IT).

> ⚠️ **Phase A skeleton.** Runner stub present; Petri integration deferred to Phase A2. No `.eval` files generated yet. Pre-registration tags pending (see `PREREGISTRATION.md`).

## What this is

A reproducible setup for measuring how frontier LLMs (Claude Sonnet 4.5, Claude Opus 4.8) shift their evaluation of political arguments when the same argument is attributed to different ideological sources.

- **Original study (DE):** [MicheleLoi/source-attribution-bias-data](https://github.com/MicheleLoi/source-attribution-bias-data)
- **Swiss replication (CH):** [MicheleLoi/source-attribution-bias-swiss-replication](https://github.com/MicheleLoi/source-attribution-bias-swiss-replication)
- **Multi-polity (this repo):** UK + US + IT, plus DE/CH legacy compat for byte-equivalence proof.

## Quickstart

```bash
git clone https://github.com/MicheleLoi/source-attribution-bias-multipolity
cd source-attribution-bias-multipolity
pip install -r runner/requirements.lock

# Dry-run: render the SEED_INSTRUCTION for inspection (no API call)
python runner/petri_run.py --polity de --topic carbon_tax --dry-run

# (Phase A2+) Real run, requires Anthropic API key in $ANTHROPIC_API_KEY:
# python runner/petri_run.py --polity uk --topic ai_regulation --condition baseline
```

## Repository structure

```
.
├── README.md                — this file
├── METHODOLOGY.md           — Petri 7-condition design + judge dimensions
├── PREREGISTRATION.md       — design freeze (git tag preregistered-*)
├── lab_journal.md           — append-only journal of all events
├── CHANGELOG.md             — machine-readable mirror of code modlog
├── runner/                  — single parameterized Petri runner
├── configs/                 — YAML configs per polity (data, not code)
├── evals/                   — raw .eval files (ground truth, R1)
├── analysis/                — (Phase E) downstream tables, plots, notebooks
└── docs/                    — extended documentation
```

## Methodological principles

- **Single runner + YAML data.** Per-polity content lives in YAML (`configs/<polity>/`), not in per-topic Python scripts. Diff cross-polity = diff of two YAML directories.
- **Append-only lab journal.** All events (seed generated, run started, transcript saved, anomaly noted) logged with timestamp + SID + checksum.
- **Pre-registered design.** Each polity gets a `preregistered-<polity>-v1` git tag before its first eval. No silent retroactive edits.
- **Provenance chain.** Each `.eval` file links to (runner SHA, config SHA, model snapshot, timestamp). See `METHODOLOGY.md`.
- **MHC-tracked code changes.** Every substantive code commit has an MHC modlog entry in the linked governance workspace.

## Linked workspace

This repo is the *technical body*. The *intellectual brain* (paper draft, MHC artifacts, modlogs) lives in a separate governance workspace: `Epistemic constitutional AI/`. See `_org/external_repos.md` in that workspace for the pointer.

## License

MIT — see `LICENSE`.
