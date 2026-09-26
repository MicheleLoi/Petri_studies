# Prospective repair of the Jev European supplement

This amendment changes the acquisition rules prospectively after an operational interruption. It is published before any repaired attempt. The original [registration](https://github.com/MicheleLoi/Petri_studies/releases/tag/preregistered-source-attribution-jev-europe-descriptive-v1) and all original observations remain preserved.

## Why a repair is needed

The first 57 client requests produced two usable responses and 55 HTTP 429 service-capacity rejections. Eighteen slots exhausted their original three-attempt allowance; 268 were untouched. No requests remained pending when the hold was audited. Collection was stopped on 26 September 2026 at approximately 10:33 UTC. Error bodies reported high upstream demand, without Retry-After headers. Both successful requests identified the required TypeSafe provider. Routing metadata on rejected requests do not establish that another provider performed an inference.

The researcher reviewed operational counts and error metadata, without examining source effects in this unfinished collection. The author explicitly adopted the following repair after being offered the alternative of retaining the exhausted slots as missing. The choice does not discard an unfavourable scientific result or reset the acquisition history.

## Exactly what changes

1. Only the eighteen named exhausted slots receive at most **three additional attempts**, for six total including their preserved original attempts. Their identities and existing-file hashes are frozen in this package.
2. The two already usable slots are never sent again. The 268 untouched slots retain at most three total attempts. First usable score per slot remains the selection rule.
3. Any **new HTTP 429 stops the entire collector immediately** after preserving that attempt and its cost uncertainty. It creates a persistent global hold; restarting does not clear it. Further resumption requires an explicit dated authorisation identifying the hold. Historical 429s remain historical and are not interpreted as a new hold.
4. Publication of this amendment must precede every new attempt. Original request timestamps are tested against the original registration. The prior run identity, original launch receipt, requests, responses and results remain unchanged; an amendment receipt and renewed-start record are added separately.

The schedule, slot IDs, block membership, source names, texts, Jev rubric, endpoint, accepted identity, score normalization, probability diagnostics and descriptive analysis are unchanged. There is no provider substitution or anonymous baseline. If the new allowance is exhausted, a slot remains missing. There is no promise that all 288 slots will be filled.

## What the interruption limits

Additional attempts are conditional on technical failure, so the acquired observations reflect the amended collection policy. Repair revisits early scheduled slots after a real interruption; chronological order is no longer a single uninterrupted pass through the original schedule. The report will retain actual timestamps, phases, errors and counts and display the original fixed halves without claiming temporal independence. This is a repair of one collection, not an independent replication. The two retained earlier observations stay identified within that history.

No new p-values, confidence intervals or equivalence verdicts are introduced. No outcome-dependent sampling expansion is permitted. The previous cumulative EUR 100 notification threshold, including next-batch reserve and uncertain costs, remains. New raw observations and the report remain private pending separate publication authorization.

## Verification and public deposit

The package identifies the exact original plan and the preserved attempt prefix using hashes. Tests check strict caps for the two slot classes, no re-sending accepted scores, immutable historical files, immediate global 429 holds, crash recovery, two publication chronologies and reporting. The public archive contains scientific code, materials, policy and integrity metadata, without credentials, private conversation/session IDs or actual response content. The dated GitHub release records public deposit; it is not a claim of immutable third-party notarization.
