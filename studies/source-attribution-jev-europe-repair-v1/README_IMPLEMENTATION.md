# Operational repair implementation

This is a new prospective amendment package. It preserves the original registered scientific plan and resumes the same private run. It does not replace an earlier registration or pretend that the interrupted collection has not begun.

The new package contains the exact original plan and manifest under `provenance/`. `PRESERVED_PREFIX.json` commits to 173 original files by SHA256: 57 request/result/response triples, the original `started.json`, and the original `launch_record.json`. Only hashes and operational counts are included; no observed rating or raw response is published. Before any new send, the runner verifies every preserved file, the original plan/manifest lineage, and both registration chronologies.

Eighteen named slots had exhausted their original three attempts. The amendment permits at most three additional attempts for each, making six in total. Every other slot retains a cap of three. The two obtained slots are never resent. Later accepted scores likewise terminate their slots. Unknown attempted dispatches consume the next numbered attempt and retain their cost reserve; saved responses are recovered without retransmission. Scientific payloads, topic texts, source labels, rubric, schedule, block assignments and planned descriptive analyses are unchanged.

The original run markers and receipt remain byte-identical. On the first amended invocation the runner creates `repair_started.json` and `amendment_launch_record.json`. Every new request records the amendment manifest hash and must have a timestamp strictly after its actual public registration. An original request is valid only after the original registration and before the amendment. The amended receipt must identify the original manifest explicitly. The original OS lock, provider transport, daily Jev documentary check and cumulative cost accounting remain in force.

## Prospective stop on HTTP 429

Every new HTTP 429 consumes its attempt and immediately stops the whole collector. An immutable `global_holds/REQUEST_SHA256.json` records the event. A restart reconstructs a missing hold even if the process died after saving the response but before saving its result/hold. Historical 429s in the committed prefix do not invoke the new rule retroactively.

No hold is automatically deleted or released. A later invocation requires a separate explicit authorization file supplied through `--resume-authorization`, with:

```json
{
  "hold_sha256": "SHA256 of the exact persisted hold JSON file",
  "authorized_utc": "A real timezone-aware authorization timestamp after the hold",
  "author_instruction": "The actual explicit instruction permitting resumption",
  "evidence": "An inspectable reference to that instruction or authorized operator record"
}
```

The release is saved immutably under `hold_releases/HOLD_SHA256.json`; the hold remains. This interface records a genuine authorization supplied by the operator. It does not generate authorization, conduct a service probe or change routing. The first repair launch does not require a release file because no prospective repair hold yet exists. A later HTTP 429 requires a new record naming that new hold.

## Reporting and chronology

The amended report retains every attempt, first-usable selection, all five planned interactions, eighteen cells and fixed halves. It reports original versus repair phase counts, attempts 1 through 6, and the operational amendment. Actual timestamps remain in the chronology plot. Planned halves are no longer uninterrupted time periods: the interruption and selective recovery must remain visible in interpretation. The report verifies original publication before the preserved prefix and amendment publication before all later requests. It cannot silently present the repaired data as an uninterrupted collection under the original retry rule.

## Commands

From the package directory, with real absolute paths supplied by the operator:

```text
python -B -m unittest discover -s code -p test_*.py -v
python -B code/repair_rehearsal.py --out NEW_SYNTHETIC_DIRECTORY
python -B code/main_runner.py verify --package AMENDMENT_PACKAGE
python -B code/main_runner.py execute --package AMENDMENT_PACKAGE --study-root PRIVATE_STUDY_ROOT --launch-record ACTUAL_AMENDMENT_RECEIPT
python -B code/main_report.py --package AMENDMENT_PACKAGE --run PRIVATE_STUDY_ROOT/runs/registered-jev-europe-v1 --out NEW_PRIVATE_REPORT_DIRECTORY
```

The actual amendment receipt has the usual public-registration, frozen-manifest, author-instruction and daily Jev-check fields, plus `original_manifest_sha256`. The parent workflow supplies publication and that genuine receipt. This file is implementation documentation, not proof of publication or authority to release a future hold.

## Offline verification completed

The final combined suite passed **27 tests**: fifteen retained tests of the original materials, rubric/parser, retry policy, daily documentary check, historical EU cost premium and OS lock; twelve repair-specific tests of exact caps and preserved science, full recovery, immutable prefix, both publication chronologies, wrong lineage, orphan request paths, no resending after usable scores, persistent global HTTP 429 holds, crash recovery, and explicit dated release. Real HTTP was forbidden throughout.

The complete synthetic rehearsal retained 57 artificial original attempts and added 286 artificial recovery attempts, producing 288 usable slots from 343 total attempts. Both descriptive panels, all five interactions, report tables and ratings/chronology plots were generated. Both figures were visually inspected; the deliberate time gap remains visible. The rehearsal uses synthetic prefix files and scores exclusively and contributes no scientific observation or API expense.
