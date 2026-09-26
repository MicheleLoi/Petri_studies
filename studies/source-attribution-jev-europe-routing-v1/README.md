# Jev Europe: admission of a documented serving route

The author approved admitting Jev through DigitalOcean provided no new account was necessary. The existing Vercel gateway account already delivered a Jev response through that route; this amendment uses the same endpoint, key and billing account. No DigitalOcean signup or credential is required.

## Scope and chronology

Previously, the acceptance rule required `finalProvider=typesafe-ai`. After 65 attempts, eight numerical ratings were present. Seven passed that gate; the eighth returned `model=typesafe-ai/jev`, one successful upstream attempt, and `finalProvider=digitalocean`. It triggered the predefined suspension. Official DigitalOcean documentation lists Jev among TypeSafe AI models: https://docs.digitalocean.com/products/inference/details/models/ . That documents a distribution route, not a verified snapshot. The presumed version remains jev-1.13.0; neither the alias nor the provider name proves the exact weights served.

This amendment admits **typesafe-ai and digitalocean** as serving routes for the same accepted Jev model identifiers, while retaining the one-upstream-attempt requirement and all other response checks. The gateway may choose either route. Record the actual final provider, returned model, route metadata and unverified-version status on every response. Provider variation must be visible in the final report; do not claim that route equivalence was tested.

The already obtained flagged response is retained as the first usable response for its slot and accepted under this amended route rule. **That eligibility decision is retrospective.** The widened rule is prospective only for subsequent requests, which must follow this public deposit. No source effects were compared to make the decision. Do not describe the entire run as having followed the widened rule from inception. No rerun or replacement of the flagged rating is permitted.

All 65 existing request/response/result triples and the old suspension are preserved by hashes. The effective execution view records the review of the one named historical result without overwriting its original identity flag. A separate release record links the old suspension to this amendment; the original suspension remains on disk. Any subsequent suspension is written separately and remains blocking.

## Unchanged scientific and operational rules

The original 288 slots, text/source payloads, order, 16 blocks, descriptive contrasts, first-valid-score selection, existing attempt caps and budget threshold remain unchanged. At least 60 seconds elapse after each call before preparing the next. Any new HTTP429 still stops globally and requires separate explicit authorization to release. Unknown providers, changed model names, multiple upstream attempts, schema or other validation problems retain the suspension rule. The same existing Vercel endpoint/key is used without payload changes.

The execution engine is a documented derivative of the frozen repair engine. `ENGINE_CHANGES.diff` shows changes to the engine class. The parser adds the named serving route; history adds the one hash-bound retrospective review. The preserved prefix and policy are public hashes, not raw results. The frozen base manifest is identified in POLICY.json, as is the unchanged pacing wrapper. The original plan file remains immutable; this text and POLICY.json explicitly override its TypeSafe-only eligibility sentence. No result is rewritten to make it appear compliant with the earlier rule.

Use `route_runner.py --study-root PRIVATE_STUDY --launch-record ORIGINAL_REPAIR_RECEIPT --route-record GENUINE_PUBLIC_ROUTE_RECEIPT` only after publication and anonymous verification. The runner requires sibling frozen repair and pacing packages. Current-date documentary checks, OS lock, persisted attempt limits and budget gates remain active. On completion use this package's `route_audit.py` and `route_report.py`, with their documented CLI options, rather than the unamended TypeSafe-only auditor.

Final reporting must retain all earlier interruptions, distinguish retrospective review from subsequent acquisition, provide serving-route counts and record the lack of snapshot verification. The descriptive analysis remains the original one. No new p-values, intervals, equivalence claim or provider-effect claim is introduced. Data, responses and reports remain private pending separate publication authorization.
