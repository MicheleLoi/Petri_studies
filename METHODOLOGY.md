# Methodology

This document describes the experimental design used across all polities (DE, CH, UK, US, IT) in the source-attribution-bias replication.

> ⚠️ **Phase A draft.** Sections drawn from `paper_full_draft.md` (Section 2 "The Finding") in the linked workspace; to be finalized at the `preregistered-uk-v1` tag.

## Theoretical framework

The study measures **source-attribution bias** in frontier LLMs: the extent to which a model's evaluation of an argument shifts when the same argument is attributed to ideologically distinct sources.

## Framework: Anthropic Petri (auditor / target / judge)

Petri ([Anthropic, 2025](https://github.com/anthropics/petri)) provides a three-agent architecture:

- **Auditor** — orchestrates the protocol, presents the same argument N times with different source attributions, rolls back the target's context between conditions.
- **Target** — the model under evaluation. Evaluates the argument on a coherence/strength scale.
- **Judge** — a separate model that scores the *target's behavior* across the N conditions on dimensions like coherence-effect-detected, source-based-reasoning, effect magnitude, and protocol execution.

## 7-condition seed design

Each topic uses 7 conditions, presented in order with rollback between each:

| # | Slot ID | Source attribution |
|---|---|---|
| 1 | `baseline` | No source / blind |
| 2 | `generic` | Generic "policy researchers" |
| 3 | `progressive_tt` | Progressive-leaning think tank |
| 4 | `conservative_tt` | Conservative-leaning think tank |
| 5 | `green_actor` | Green party / environmental actor |
| 6 | `right_actor` | Right-of-centre political actor |
| 7 | `neutral_institution` | Neutral institution (e.g., statistical office) |

The exact mapping per polity (which think tank, which politician) is in `configs/<polity>/source_coding_ratified.yaml`. The coding requires human ratification before the polity's seeds run (gating item). See `docs/source_coding_protocol.md`.

## Judge dimensions (polity-invariant)

See `configs/_shared/judge_dimensions.yaml`. Phase A: stub; Phase B: validated against the `COHERENCE_DIMENSIONS` dicts in the legacy DE/CH scripts.

## Models tested

- **Claude Sonnet 4.5** (snapshot: TBD at pre-registration)
- **Claude Opus 4.8** (snapshot: TBD at pre-registration)

Within-family comparison: addresses "does the effect scale with model capability?" but does not address cross-vendor generalization.

## Anti-spoiler discipline

The DE iteration found ~1/3 of evaluations spoiled by meta-awareness (target detecting systematic testing). Mitigations carried over to all polities:
- No explicit framing as "testing for bias".
- Vary surface details (formatting, ordering) without changing semantic content.
- Tag and exclude spoiled runs in analysis; report spoilage rate in published tables.

## Pre-registration discipline

Before the first real `.eval` is generated for a polity, `git tag preregistered-<polity>-v1` is placed on the commit that freezes the design. All published `.eval` files must have timestamps strictly later than the tag's commit date.

## Provenance chain

Each `.eval` file embeds:
- Runner commit SHA (this repo)
- Config file SHA-256
- Model snapshot identifier
- Timestamp (ISO-8601, UTC)
- Random seed (if applicable; Petri default is non-stochastic for judge)
- Petri version (from `runner/requirements.lock`)

## References

- Anthropic Petri framework: <https://github.com/anthropics/petri>
- Inspect-AI: <https://github.com/UKGovernmentBEIS/inspect_ai>
- Paper draft: `paper_full_draft.md` in linked workspace `Epistemic constitutional AI/`.
