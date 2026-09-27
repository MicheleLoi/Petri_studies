# Jev Europe: bounded gateway failover

The author approved: “approvo, non è necessario tutti da uno, continuiamo a testare”, in response to the proposal to admit a maximum of two internal gateway attempts between the two approved providers, with the first failing technically and a single final result. The existing Vercel account, endpoint and key remain in use.

## Adopted acquisition rule

Both TypeSafe AI and DigitalOcean remain admitted serving routes for the same Jev identifiers. In addition to the already admitted one-upstream case, accept two sequential upstream attempts only when the metadata identify one accepted Jev model, both providers are admitted, the first attempt failed with a transient technical HTTP status (408,500,502,503,504,529), and the second and final attempt alone succeeded with200. Provider/model attempt counts must agree with the recorded lists and timestamps. Unknown providers/models, ambiguous metadata, more than two attempts or multiple successes remain grounds for suspension. Any internal or client-visible429 still stops collection globally. There is no automatic release of subsequent holds or suspensions.

One worker and a minimum60-second interval after each client call remain in force. Internal gateway failover is not a second independently selected rating: the client receives one result. The failed upstream operation may nevertheless have consumed computation or incurred cost. Preserve both provider attempts and separately report client requests and internal attempts. The original ledger is unchanged; a parallel conservative estimate adds EUR0.01 for each recorded failed internal call, which may double-count costs already covered by the gateway's reported charge. Retain the EUR100 warning gate including the next-batch reserve. Costs remain estimates, not verified invoices.

## Historical review and prospective scope

Before this amendment there were73 client attempts and16 readable ratings. The latest response reported DigitalOcean503 followed by TypeSafe AI200, for the same Jev model identifier. It was suspended under the previous single-upstream rule. The author now admits that existing result retrospectively, preserving its original flag and the suspension. No response is replaced or resent. The separate earlier review of the one DigitalOcean-served response also remains visible. The broadened failover rule is prospective only for requests after this deposit; do not describe either historical review as having been preregistered before its observation.

All73 request/response/result triples, both historical suspensions and the earlier release are preserved by hashes. Effective history presents the two explicit, hash-bound reviews without rewriting the raw archive. New suspensions are stored separately. Source contrasts have not been examined during the unfinished collection. Previously obtained slots, first-valid selection, original scientific payloads, order, blocks, attempt caps and descriptive analysis remain unchanged.

The exact served snapshot and equivalence between hosting routes are unverified. Jev1.13.0 remains a documentary presumption for the unversioned gateway alias. A dated check must precede each new UTC-day launch/resume, and be saved separately from historical launch records. This amendment spans an additional day; disclose the interruption and extended observation period.

## Execution and outputs

Publish and verify this package before executing `fallback_runner.py --study-root PRIVATE_STUDY --launch-record CURRENT_DATED_REPAIR_RECEIPT --fallback-record GENUINE_FALLBACK_RELEASE_RECEIPT`. Sibling frozen repair, pacing and routing packages are dependencies identified by hashes. The code derives from the registered route engine; CHANGES.diff records the change. It preserves the OS lock, budget gate and attempt ledger. Old collectors must not be resumed.

At completion use `fallback_audit.py --study-root PRIVATE_STUDY --out NEW_AUDIT_JSON`, then `fallback_report.py --study-root PRIVATE_STUDY --audit NEW_AUDIT_JSON --out NEW_PRIVATE_REPORT_DIR`. The audit must succeed before source-effect analysis. The descriptive computations remain original; disclosures distinguish acquisition phases, internal attempts, both historical reviews, providers and unverified snapshots. No new p-values, confidence intervals, equivalence verdicts or provider-effect claims are introduced. Raw data and report remain private pending separate publication authorization.
