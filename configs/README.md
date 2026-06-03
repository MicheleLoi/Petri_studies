# configs

YAML configurations driving the runner. **Data, not code.**

## Structure

```
configs/
├── _shared/
│   ├── judge_dimensions.yaml   — Petri judge dims (polity-invariant)
│   └── seed_skeleton.yaml      — 7-condition structural skeleton
├── de/                          — legacy compat (rigenera DE byte-per-byte; Phase B)
├── ch/                          — legacy compat (Phase B)
├── uk/                          — Phase D+
├── us/                          — Phase E
└── it/                          — Phase E
```

(Phase A: only `_shared/` populated. Polity directories created when their respective phases begin.)

## Per-polity files

Each `configs/<polity>/` contains:

- `source_coding_ratified.yaml` — **GATING**. Maps the 7 structural slots (baseline, generic, progressive_tt, …) to actual polity-specific entities (think tanks, politicians, institutions). Requires explicit human ratification before any seed runs. See `../docs/source_coding_protocol.md`.
- `<topic>.yaml` (one per topic) — argument text + 7-condition expansion using the ratified source coding.

## Validation

All `<topic>.yaml` files are validated against `../runner/schema.json`. Required keys:

- `polity` — one of `[de, ch, uk, us, it]`
- `topic` — string
- `argument` — string ≥ 50 chars
- `conditions` — array of exactly 7 condition objects, each with `id` (and optional `source`, `notes`)

## Adding a topic to a polity

See `../docs/adding_a_polity.md`.
