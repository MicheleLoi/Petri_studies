# Source attribution: descriptive study, public package v1

**Prepared for public preregistration; publication and main collection have not occurred at preparation time.** The GitHub release's actual publication time and its exact commit identify the public preregistration. A local preparation timestamp is not a publication receipt.

Start with [PREREGISTRATION.md](PREREGISTRATION.md). The study fixes two arguments, four source names, four systems and 32 blocks: 1,024 planned observations. It reports the two source pairs separately using descriptive analysis, without formal hypothesis tests or equivalence verdicts. Jev's version is explicitly presumed and its scoring interface differs from the chat systems.

- [plan.json](plan.json): complete request specifications and planned order, unchanged from the verified preparation snapshot.
- [materials](materials): exact texts, chat messages, settings and Jev rubric. Historical status/provenance fields describe the preparation record; the complete current plan is the preregistration and plan.json.
- [code](code): unchanged tested collector, parsers, report and supporting code. main_runner.py and main_report.py are the study entry points; older helper functions in design.py are not the adopted analysis.
- [verification/tests.txt](verification/tests.txt) and [synthetic verification](verification/synthetic-verification.json): previously completed offline tests and artificial-data checks. Artificial observations are not empirical evidence.
- [PUBLIC_PROVENANCE.json](PUBLIC_PROVENANCE.json): byte identity and documented metadata changes relative to the private preparation snapshot.
- [VERIFYING.md](VERIFYING.md): independent verification using SHA-256 and the Python standard library; no Giano source or access is required.
- [OPERATIONS.md](OPERATIONS.md): verification, publication and execution procedure.

This package contains scientific study software, not Giano application source. Private conversations, session identifiers, Giano records, API credentials and real response archives are excluded. The original non-secret Vertex project identifier is retained in endpoint/configuration strings to preserve the exact tested request specifications; authorization values are supplied privately at runtime.

The private preparation snapshot remains preserved. Its manifest hash connects this public derivative to private project provenance without publishing that history. No Giano attestation of this public package is claimed merely because a manifest exists. Amendments must be dated, explained and published as later versions while this version is preserved.
