# runner

Single parameterized entrypoint for the multi-polity replication. **No per-topic scripts; no hardcoded seeds.**

## Architecture (Phase A skeleton)

```
runner/
├── petri_run.py        — CLI + YAML load + schema validation + template render
├── template.j2         — Jinja2 template producing the SEED_INSTRUCTION string
├── schema.json         — JSON Schema for YAML configs
├── requirements.lock   — pinned dependencies (Petri pin pending Phase A2)
└── tests/
    └── test_template_render.py   — unit tests for the rendering pipeline
```

## CLI

```bash
python petri_run.py --polity {de|ch|uk|us|it} --topic <topic> [--condition <id|all>] [--dry-run] [--reproduce]
```

- `--dry-run` — print rendered SEED_INSTRUCTION and exit (no model call). Works in Phase A.
- `--reproduce` — Phase D+ — verify byte-equivalence against a published `.eval`.
- Without `--dry-run` and without Phase A2 Petri integration, the runner exits with a clear stub message.

## Phase A vs Phase A2

| Item | Phase A (this commit) | Phase A2 (after Petri version pin) |
|---|---|---|
| CLI scaffolding | ✓ | ✓ |
| YAML load + schema validation | ✓ | ✓ |
| Template rendering | ✓ | ✓ (+ refined in Phase B) |
| Petri import | ✗ (not yet) | ✓ (`from petri.solvers.auditor_agent import auditor_agent`) |
| API call to Anthropic | ✗ | ✓ |
| `.eval` file written | ✗ | ✓ |
| Lab journal entry written | ✗ | ✓ |
| Harness placement log call | ✗ | ✓ |

## Testing

```bash
pip install -r requirements.lock
pytest tests/
```

Phase A tests only the rendering pipeline. Phase B adds byte-equivalence tests against DE/CH legacy SEED_INSTRUCTION strings (see `legacy_compat.py` once added).
