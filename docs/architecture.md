# Architecture

Three-layer separation. **This is the core methodological invariant of the multi-polity replication.**

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Petri SDK (external dependency)                    │
│  - Vanilla, unmodified                                       │
│  - from petri.solvers.auditor_agent import auditor_agent     │
│  - from petri.scorers.judge   import alignment_judge         │
│  - Wrapped by Inspect-AI                                     │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Runner (this repo, fixed across polities)          │
│  - runner/petri_run.py                                       │
│  - runner/template.j2                                        │
│  - runner/schema.json                                        │
│  - One file, parameterized via CLI args + YAML configs       │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Configs (this repo, per-polity, DATA not code)     │
│  - configs/<polity>/source_coding_ratified.yaml              │
│  - configs/<polity>/<topic>.yaml                             │
│  - Drives Layer 2; never executable                          │
└─────────────────────────────────────────────────────────────┘
```

## Why this separation

The DE/CH iterations used per-topic Python scripts with hardcoded seeds: `study4_<topic>.py × N × _patched/_fixed/_simplified` variants — ~50 files total in `~/Petri_studies/` (now archived as `~/Petri_studies/_archive/`). This created chronic drift:

- Cross-topic methodological changes required editing many files.
- Cross-iteration drift was invisible until merge.
- The lab book proliferated (`study4_lab_book_v1.md` → `_v5.md`) because each runner mutation tempted a new book.

The multipolity replication explicitly cures this:

- The methodological invariant (Petri + 7-condition + judge dims + anti-spoiler discipline) lives in **one** runner file. Editing it once is enough.
- Polity-specific content lives in YAML. **Diff between UK and US is a diff of two data directories.**
- Adding a new polity (e.g., France post-IT) is a new YAML directory, not new Python.

## Why Jinja2 template instead of dict-to-Petri

Petri's `auditor_agent` consumes a single narrative string (the `SEED_INSTRUCTION`) describing the N-step protocol. It does NOT accept a structured dict — verified by reading the legacy DE/CH scripts before this repo was created (see plan §4.1 in the linked workspace).

The template generates this narrative from structured YAML data. This:

- Keeps Petri vanilla (no fork, no monkeypatch, no version drift risk).
- Allows machine-readable diff at the YAML layer.
- Allows human-readable inspection at the rendered SEED_INSTRUCTION layer (`petri_run.py --dry-run`).
- Enables byte-equivalence proof against DE/CH legacy scripts (Phase B `legacy_compat.py`).

## Provenance and reproducibility

See `METHODOLOGY.md` for the embedded provenance per `.eval` file and `reproducing_de_ch.md` (Phase B) for the legacy compat protocol.
