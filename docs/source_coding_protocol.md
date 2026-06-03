# Source Coding Protocol

Criteria for ratifying `configs/<polity>/source_coding_ratified.yaml`.

> ⚠️ Phase A skeleton — content to be expanded after the UK pilot.

## Purpose

The source coding maps the 7 structural slots (`baseline`, `generic`, `progressive_tt`, `conservative_tt`, `green_actor`, `right_actor`, `neutral_institution`) to actual polity-specific entities (think tanks, politicians, institutions). The coding is **the load-bearing methodological step** — once it is in place, the runner can mechanically generate seeds. Until it is in place, no seed is valid.

## Ratification requirements

1. **At least one human coder** familiar with the polity's political landscape (think tanks, party system, institutions).
2. **Plural perspective ideal.** A pair of coders (one left-leaning, one right-leaning) reviewing each other's mapping reduces single-bias risk.
3. **Written criteria.** Each entity assigned to a slot has a one-line rationale recorded in the YAML (e.g., "Resolution Foundation: UK progressive economic think tank, founded 2005, focus on living standards").
4. **Disagreement protocol.** If coders disagree on a slot assignment, escalate to a third coder OR mark the slot as `[disputed]` and exclude that condition from the study (transparent gap > forced consensus).

## Slot definitions (polity-invariant)

See `configs/_shared/seed_skeleton.yaml` for the canonical definitions.

## YAML format for ratified coding

```yaml
polity: uk
ratified_by:
  - name: <coder name or pseudonym>
    role: <e.g., "domain expert", "primary investigator">
    date: 2026-XX-XX
slots:
  generic:
    entity: "Policy researchers"
    rationale: "Catch-all term used in academic writing; no ideological marker."
  progressive_tt:
    entity: "Resolution Foundation"
    rationale: "UK progressive economic think tank, founded 2005, focus on living standards and inequality. Widely cited in left-of-centre economic discourse."
  conservative_tt:
    entity: "Institute of Economic Affairs"
    rationale: "UK conservative/free-market think tank, founded 1955. Widely cited in right-of-centre economic discourse."
  green_actor:
    entity: "Caroline Lucas (Green Party MP)"
    rationale: "Long-serving Green Party MP; recognizable representative of UK Green political position."
  right_actor:
    entity: "Suella Braverman (Conservative MP)"
    rationale: "Recognizable right-of-centre Conservative MP; clear right positioning on multiple policy areas."
  neutral_institution:
    entity: "Office for National Statistics"
    rationale: "UK official statistical agency; non-partisan, technical mandate."

disputed:  # if any slots disputed
  - slot: <slot_id>
    notes: <free text>
```

## Polity-specific notes

(To be filled per polity at the time of ratification. Examples to record here when relevant:)
- **IT:** Italian nuclear referendum history (1987, 2011) may interact with the `nuclear_energy` topic — record whether this is treated as confounder or design feature.
- **US:** Two-party dynamic vs European multi-party — may require remapping `green_actor` and `right_actor` slots.
- **UK:** Post-Brexit political realignment — `progressive_tt` and `conservative_tt` selections should reflect current rather than pre-2016 landscape.
