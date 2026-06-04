# Pre-registration

Each polity's design is frozen at a specific git commit, tagged `preregistered-<polity>-v1`.

## Discipline

- **No retroactive edits** to the design (`configs/<polity>/*.yaml`, `runner/`, `METHODOLOGY.md`) without a versioned `preregistered-<polity>-v2` tag + a written justification in `CHANGELOG.md`.
- **All published `.eval` files** must have ISO-8601 timestamps strictly after the corresponding pre-registration tag's commit date.
- **A revised pre-registration** invalidates prior `.eval` files for that polity unless explicitly re-tagged.

## Polity status

| Polity | Tag | Design freeze date | Source coding ratified | First eval date | Status |
|---|---|---|---|---|---|
| DE | (legacy compat — original study external) | n/a | n/a | n/a | Reference only |
| CH | (legacy compat — Swiss replication external) | n/a | n/a | n/a | Reference only |
| UK | `preregistered-uk-v1` (TBD) | TBD — deferred to post-trial | ✓ Ratified 2026-06-04 (commit 9c78b84) | n/a | **Trial mode**: iterating on protocol via `carbon_tax` only; pre-registration deferred until protocol validated. |
| US | `preregistered-us-v1` | TBD | ⏳ Pending | n/a | Phase E |
| IT | `preregistered-it-v1` | TBD | ⏳ Pending | n/a | Phase E |

## Pre-registration content per polity

When a polity's design is frozen, the following must be specified and tagged:

1. **Topics** to be evaluated (e.g., AI regulation, AI security, carbon tax, nuclear energy, native fiscal topic).
2. **Source coding** (`configs/<polity>/source_coding_ratified.yaml`) — which think tanks / politicians map to which ideological slot. Human-ratified.
3. **Argument texts** — full text for each topic.
4. **Models** — exact snapshot identifiers (e.g., `claude-sonnet-4.5-20260101`).
5. **Judge dimensions** — typically polity-invariant (`configs/_shared/judge_dimensions.yaml`); if a polity-specific judge dimension is added, it is noted here.
6. **Sample size** — number of evaluations per condition per model.
7. **Anti-spoiler protocol** — how meta-awareness mitigation is implemented for this polity.
8. **Stopping rule** — what conditions terminate the polity's data collection.

## Deviations log

Once a polity is pre-registered, any deviation must be logged in `CHANGELOG.md` with rationale, and may require a `-v2` re-tag.

(No deviations yet — Phase A skeleton.)
