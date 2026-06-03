# Lab Journal

Append-only journal of all events in this repository. **One entry per event.** Never edit past entries; corrections go as new entries below.

## Format

```
## [ISO-8601 timestamp] [SID] [event_type]
**Polity:** <polity or "n/a">
**Topic:** <topic or "n/a">
**Condition:** <condition id or "n/a">
**Files:** <list of files touched>
**Notes:** <free-text>
```

`event_type` is one of: `bootstrap`, `config_drafted`, `config_ratified`, `seed_rendered`, `run_started`, `run_completed`, `eval_saved`, `eval_published`, `anomaly`, `correction`, `decommission`, `tag`, `note`.

---

## [2026-06-03] [SID-20260603-095328] [bootstrap]
**Polity:** n/a
**Topic:** n/a
**Condition:** n/a
**Files:** all (Phase A skeleton)
**Notes:** Repository bootstrap. Phase A skeleton created per plan `~/.claude/plans/as-we-go-pianifica-l-estensione-dello-serialized-pizza.md` §5 Fase A. License MIT. No Petri imports yet — runner stub validates YAML + renders Jinja2 template. First commit follows. Linked governance workspace: `Epistemic constitutional AI/` (path: `C:\Users\loimi\switchdrive\CURRENTLY WORKING ON\AI - assisted papers\Epistemic constitutional AI\`).

## [2026-06-03] [SID-20260603-095328] [first_commit]
**Polity:** n/a
**Topic:** n/a
**Condition:** n/a
**Files:** 20 (root-commit)
**Notes:** Phase A skeleton committed as `63fda01` on branch `main`. pytest runner/tests/ → 9/9 PASS in 0.30s. MHC ref: MOD-001 in workspace `03_modification_logs/ModificationLog_Code_Multipolity_runner.md`. License MIT, no Petri imports yet.

## [2026-06-03] [SID-20260603-095328] [legacy_compat_match]
**Polity:** de
**Topic:** carbon_tax
**Condition:** all (7 conditions in one SEED_INSTRUCTION)
**Files:** runner/template.j2, runner/schema.json, runner/petri_run.py, runner/legacy_compat.py, configs/de/source_coding.yaml, configs/de/carbon_tax.yaml
**Notes:** `legacy_compat.py --polity de --topic carbon_tax` reproduced the SEED_INSTRUCTION hardcoded in `~/Petri_studies/study4_carbon_tax_patched.py` (2025-12-13) **byte-for-byte**: 3498 chars, 104 newlines. Phase B gate satisfied for DE.

## [2026-06-03] [SID-20260603-095328] [legacy_compat_match]
**Polity:** ch
**Topic:** carbon_tax
**Condition:** all (7 conditions in one SEED_INSTRUCTION)
**Files:** configs/ch/source_coding.yaml, configs/ch/carbon_tax.yaml (template/runner already enhanced by the DE pass — same commit)
**Notes:** `legacy_compat.py --polity ch --topic carbon_tax` reproduced the SEED_INSTRUCTION from `~/Petri_studies/run_swiss_carbon_tax.py` (2026-01-13) **byte-for-byte**: 3052 chars, 90 newlines. Template required two new parameters: `objective_descriptor` (CH says "carbon pricing" in Objective, "climate policy" in Steps — DE uses one descriptor everywhere) + `include_auditor_communication_style` flag (CH omits the section DE includes). Phase B gate satisfied for CH.

## [2026-06-03] [SID-20260603-095328] [commit]
**Polity:** n/a
**Topic:** n/a
**Condition:** n/a
**Files:** 9 (Phase B substantive content: 4 modified + 5 new)
**Notes:** Phase B committed as `98fc6d4` on branch `main`. pytest 11/11 PASS in 0.31s. MHC ref: MOD-002 in workspace modlog. Audit trail companion (this lab_journal update + CHANGELOG mirror) lagging by one commit (this commit, MOD-003, follows).
