# Changelog

Machine-readable mirror of MHC code modlog entries for this repository. Each entry corresponds to a `MOD-NNN` in the linked workspace's `03_modification_logs/ModificationLog_Code_*.md` files.

## Format

```
## [commit_sha_short] — [change_type] — YYYY-MM-DD
**MHC ref:** MOD-NNN in ModificationLog_Code_<context>.md
**Files:** <list>
**Rationale:** <one paragraph>
**Affects evals:** <list of .eval files invalidated or "none">
```

---

## `63fda01` — creation — 2026-06-03

**MHC ref:** MOD-001 in `03_modification_logs/ModificationLog_Code_Multipolity_runner.md` (linked workspace)

**Files:** 20 (root-commit) — `LICENSE`, `.gitignore`, `README.md`, `METHODOLOGY.md`, `PREREGISTRATION.md`, `lab_journal.md`, `CHANGELOG.md`, `runner/{README.md,petri_run.py,template.j2,schema.json,requirements.lock,tests/test_template_render.py}`, `configs/{README.md,_shared/judge_dimensions.yaml,_shared/seed_skeleton.yaml}`, `evals/README.md`, `docs/{architecture.md,adding_a_polity.md,source_coding_protocol.md}`.

**Rationale:** Bootstrap del repo della replicazione UK/US/IT (plan §5 Fase A, SID-20260603-095328). Implementa single-runner architecture (D1) + monorepo structure (D2) + lab journal append-only (D3) + code modlog discipline (D4). Phase A scope-limited: niente Petri SDK, niente API call, niente `.eval` generati. Runner stub valida YAML + rende Jinja2 template; pytest 9/9 PASS. License MIT.

**Affects evals:** `none (skeleton only)` — Phase A non genera alcun `.eval`; nessun `.eval` storico invalidato.

---

## `98fc6d4` — feature — 2026-06-03

**MHC ref:** MOD-002 in `03_modification_logs/ModificationLog_Code_Multipolity_runner.md`

**Files:** 9 (4 modified + 5 new) — modified `runner/{petri_run.py,template.j2,schema.json,tests/test_template_render.py}`; new `runner/legacy_compat.py`, `configs/de/{source_coding.yaml,carbon_tax.yaml}`, `configs/ch/{source_coding.yaml,carbon_tax.yaml}`.

**Rationale:** Phase B gate (plan §5 Fase B) — prova byte-equivalence tra il nuovo pipeline e gli script DE/CH storici. `legacy_compat.py --polity de --topic carbon_tax`: MATCH 3498 char / 104 NL vs `~/Petri_studies/study4_carbon_tax_patched.py`. `legacy_compat.py --polity ch --topic carbon_tax`: MATCH 3052 char / 90 NL vs `~/Petri_studies/run_swiss_carbon_tax.py`. Template esteso con `objective_descriptor` + `step_descriptor` separati (CH usa "carbon pricing" / "climate policy" asimmetria) e `include_auditor_communication_style` flag (CH omette la sezione DE include). Trailing newline normalization in Python (DE `\n\n`, CH `\n`). Schema esteso (mantenuto `additionalProperties: false`), default backward-compatible. pytest 11/11 PASS.

**Affects evals:** `none — proof of equivalence is retroactive; no .eval files generated yet`. Garantisce che la rimozione futura degli script hardcoded NON cambierà l'esperimento per i topic carbon_tax DE+CH.

---

(Next entry: MOD-003 — audit trail companion + workspace integration, commit in progress.)
