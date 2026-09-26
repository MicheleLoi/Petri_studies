# Execution and reporting

Run commands from this package's `code/` directory, with explicit absolute paths as appropriate. The tested environment is recorded in `ENVIRONMENT.json`. Verification performs no inference:

```text
python -B main_runner.py verify --package PACKAGE
```

Publish the exact frozen package and manifest, verify anonymous retrieval and save the real publication URL/time privately. The launch record needs registration_reference, registered_utc, visibility public, manifest_sha256 and author_launch_instruction. It also needs jev_version_recheck_utc, jev_version_evidence and jev_presumed_model. The documentary check must be from the actual launch/resume UTC date. Version remains presumed; a date does not certify deployment identity.

```text
python -B main_runner.py execute --package PACKAGE --study-root PRIVATE_STUDY_ROOT --launch-record PRIVATE_LAUNCH_RECORD
```

Run directory: PRIVATE_STUDY_ROOT/runs/registered-jev-europe-v1. Preserve all attempts. The OS-owned execution lock must never be deleted to force access. Verify a collector's PID, creation time, executable and command before considering resumption; access denied is not evidence that it died. Resume only after confirmed process termination, with the same frozen package, genuine launch record and fresh dated identity check when required. Never clear suspensions or attempt counters automatically. An interrupted request remains attempted with uncertain cost. No automatic provider fallback or scientific design change is permitted.

Observe counts, errors, suspensions, hashes and cumulative costs during collection. Do not inspect source effects until completion. The inherited budget includes earlier runs, explicit uncertain-cost reserves and historical Gemini EU premiums; its EUR conversion is a conservative accounting convention, not an invoice. Warn the author before any batch would reach EUR 100 including reserve. A pricing increase or unexpected identity requires review.

Once finished.json exists, verify 288 planned slots against obtained/missing counts, all attempts and hashes, served identity, and publication before the first scientific request. Generate the report once in a fresh private directory:

```text
python -B main_report.py --package PACKAGE --run PRIVATE_STUDY_ROOT/runs/registered-jev-europe-v1 --out PRIVATE_STUDY_ROOT/reports/registered-jev-europe-v1
```

Inspect all eighteen cells, five contrasts, two fixed halves and figures. Retain native scale and auxiliary diagnostics. The report contains no p-values, confidence intervals, equivalence verdicts or generated prose explanations attributed to Jev. Any later analysis must be identified as additional. Preserve synthetic and neutral checks separately from scientific observations. Update human-readable and structured private work records; do not treat a completed computation as author ratification or established mechanism.
