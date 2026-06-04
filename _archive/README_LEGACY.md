# README — archived 2026-06-03

> **This folder is NOT authoritative.** Until 2026-06-03 it was `~/Petri_studies/` and held the live Python scripts that generated the published `.eval` files for the German (DE) and Swiss (CH) iterations of the source-attribution-bias study.

## Why archived

The scripts were per-topic Python with hardcoded `SEED_INSTRUCTION` strings (~50 files including `_patched` / `_fixed` / `_simplified` / `_v1` variants). The cross-topic methodological invariants kept drifting because each topic was its own world.

Replaced 2026-06-03 by `C:\Users\loimi\Petri_studies\` — a single git-versioned repo with one parameterized Petri runner + YAML configs per polity/topic. The new pipeline reproduces the `SEED_INSTRUCTION` of the DE+CH carbon_tax legacy scripts **byte-for-byte** (proven by `runner/legacy_compat.py`: MATCH 3498 char / 104 NL for DE, 3052 char / 90 NL for CH).

## What to do if you find this folder

- **Want to look at a historical script?** It's still here, read-only. Look around.
- **Want to RUN a historical script?** Don't. Use the canonical repo instead: `Petri_studies` and run `python runner/petri_run.py --polity de --topic carbon_tax --dry-run`. It reproduces the same SEED_INSTRUCTION.
- **Want to MODIFY one of these files to change the experiment?** **Do not.** Modify the corresponding YAML in `Petri_studies/configs/<polity>/<topic>.yaml` and create a `MOD-NNN` entry in the workspace's `03_modification_logs/ModificationLog_Code_Multipolity_runner.md`.

## Provenance

- **Last live state:** filesystem timestamps as of 2026-06-03 ~14:00 (Europe/Zurich).
- **Decommission ratified:** plan `~/.claude/plans/as-we-go-pianifica-l-estensione-dello-serialized-pizza.md` §5 Fase C, SID-20260603-095328.
- **Canonical replacement:** `C:\Users\loimi\Petri_studies\` at commit `6139404` (Phase C audit trail companion, branch `main`).
- **Workspace note:** `Epistemic constitutional AI/09_notes/_decommissioned_petri_studies.md`.
- **Harness ledger entry:** in `Epistemic constitutional AI/_org/harness_log.jsonl`.

## Two published `.eval` archives (unrelated, untouched)

- <https://github.com/MicheleLoi/source-attribution-bias-data> — original DE study `.eval` files
- <https://github.com/MicheleLoi/source-attribution-bias-swiss-replication> — CH replication `.eval` files

These GitHub archives are NOT affected by this archive. They remain canonical for the historical DE+CH studies.

---

*Generated 2026-06-03 (SID-20260603-095328).*
