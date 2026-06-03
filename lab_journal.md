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
