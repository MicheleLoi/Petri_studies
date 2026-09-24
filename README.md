# Petri_studies

**Multi-polity replication of the source-attribution-bias study** (Anthropic Petri framework / Inspect-AI), extending the German (DE) and Swiss (CH) iterations to the United Kingdom (UK), United States (US), and Italy (IT).

> **Status (2026-06).** Harness operational (Petri / Inspect-AI integration complete). **428 `.eval` files** across DE/CH (legacy, byte-equivalence-verified), UK, and US; IT pending. E1 (prestige × stance deconfound) is pre-registered — git tag `preregistered-e1-v1`. Many runs are **exploratory / in-progress and not peer-reviewed**; the append-only [`lab_journal.md`](lab_journal.md) is the authoritative record (including corrections and superseded results) — read findings there with their in-progress framing.

## What this is

A reproducible setup for measuring how frontier LLMs (Claude Sonnet 4.5, Claude Opus 4.8) shift their evaluation of political arguments when the same argument is attributed to different ideological sources.

- **Original study (DE):** [MicheleLoi/source-attribution-bias-data](https://github.com/MicheleLoi/source-attribution-bias-data)
- **Swiss replication (CH):** [MicheleLoi/source-attribution-bias-swiss-replication](https://github.com/MicheleLoi/source-attribution-bias-swiss-replication)
- **Multi-polity (this repo):** UK + US + IT, plus DE/CH legacy compat for byte-equivalence proof.

## Quickstart

```bash
git clone https://github.com/MicheleLoi/Petri_studies
cd Petri_studies
pip install -r runner/requirements.lock

# Dry-run: render the SEED_INSTRUCTION for inspection (no API call)
python runner/petri_run.py --polity de --topic carbon_tax --dry-run

# Real run (requires ANTHROPIC_API_KEY in env; see runner/README.md for the model-role flags):
# python runner/petri_run.py --polity us --topic ai_security_e1 --execute \
#   --arm fresh_per_condition --target anthropic/claude-sonnet-4-5-20250929 \
#   --auditor anthropic/claude-haiku-4-5-20251001 --judge anthropic/claude-haiku-4-5-20251001
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
- **Append-only lab journal.** All events (seed generated, run started, transcript saved, anomaly noted) remain in the journal with their original provenance fields. New Giano session provenance is recorded separately by Giano; missing historical links stay explicit rather than being assigned to the current session.
- **Pre-registered design.** Each polity gets a `preregistered-<polity>-v1` git tag before its first eval. No silent retroactive edits.
- **Provenance chain.** Each `.eval` file links to (runner SHA, config SHA, model snapshot, timestamp). See `METHODOLOGY.md`.
- **Current work tracing.** Open this repository as a Giano T tracked folder and use the `giano-tracing` assistant plugin. The assistant proposes entries; the human accepts or rejects them in Giano. Giano owns its register and attestations.

## Historical governance workspace

The separate `Epistemic constitutional AI/` workspace contains historical paper drafts, MHC artifacts and modlogs. Those records remain evidence, but this repository no longer calls its harness or reads its current SID. Current research work uses Giano T in this folder; changing the tracing layer does not alter the pre-registered design or the configured target, auditor and judge models.

## License

MIT — see `LICENSE`.


## Prospective descriptive study (September 2026)

[Public preregistration package](studies/source-attribution-descriptive-v1/README.md): two fixed arguments, four named sources, four systems and 1,024 planned slots; descriptive analysis. Prepared locally for publication; consult the corresponding GitHub release for the actual public registration record. The new study is separate from the historical Petri/E1 preregistrations above. Current private deliberation and Giano tracing remain in the private research workspace; only the scientific package is exported here.
