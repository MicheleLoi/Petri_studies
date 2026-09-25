# Execution and reporting

Read `PREREGISTRATION.md` for the study and `PROTOCOLLO.md` for the Italian explanation. `plan.json` fixes 1,664 slots and all payloads. This package must first be publicly registered. Neither these commands nor a local manifest establish publication.

## Before collection

Run the offline tests and package verification with the exact Python and dependency versions recorded in `ENVIRONMENT.json`. No credentials are needed for verification.

```
python -B -m unittest discover -s code -p "test_*.py" -v
python -B code/main_runner.py verify --package .
```

Use environment variables `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from the existing private credential setup. Never place their values in the package or logs. Destinations are only `https://api.openai.com/v1/chat/completions` and `https://api.anthropic.com/v1/messages`. Four neutral configuration checks have passed; their raw responses remain private and excluded from the study.

After actual public registration, create a private launch record with the genuine publication URL, `registered_utc`, `visibility: public`, the exact file SHA256 of `MANIFEST.json`, and the author's actual launch instruction. Do not fabricate a receipt or timestamp. Record the process ID, process creation time and command separately when launching. Store the true release commit and any package archive hash with the publication evidence. Inspect the repository history being published before pushing.

## Collection

From the exact published package, with explicit absolute paths substituted:

```
python -B code/main_runner.py execute --package <published-package> --study-root <private-study-design> --launch-record <private-launch-record.json>
```

The run is `<private-study-design>/runs/registered-extension-v1`. The historical `registered-study-v1` is untouched. Requests are written before dispatch; attempts and responses are exclusive append-only artifacts. Four worker groups prevent simultaneous on/off requests to the same base model. Version/configuration suspensions apply to that entire group. Other groups may continue.

Never delete `execution.lock` to bypass its OS lock, start a duplicate collector, overwrite an attempt or erase a suspension. On interruption, verify PID, creation time and command before resumption. Resume using the same package and launch record; the code recovers saved responses offline and does not resend a persisted attempt. Each slot retains a maximum of three total attempts. The heartbeat may inspect progress, errors, suspensions, time and cost, but must not analyze source effects during collection.

Cost checks include all request records under the private study root, historical Gemini EU premiums and explicit unknown-outcome reserves. Reserves are EUR 0.04 per ordinary attempt and EUR 0.15 per reasoning attempt. Before each block, all still-permitted attempts in that block are reserved; the runner stops for notice if cumulative estimates plus this reserve reach EUR 100. Do not bypass the stop or raise the threshold automatically. Provider billing may differ from full-price token planning estimates.

## Completion

After `finished.json`, verify planned and obtained counts, attempt limits, request/response/payload hashes, served IDs and publication-before-first-request chronology. The report CLI checks completion, launch-manifest identity and every request timestamp before producing source comparisons.

```
python -B code/main_report.py --package <published-package> --run <private-study-design>/runs/registered-extension-v1 --out <new-private-report-directory>
```

The output directory must not already exist. The report contains all 12 case/configuration panels, the specified pairs and halves, first planned usable illustrations, configuration comparisons, raw-source hashes and descriptive charts. No p-values, confidence intervals or equivalence verdicts are generated. A missing rating is reported, not imputed. Output stays private pending separate authorization to publish results.

Update the private human diary and structured events, distinguish observations from interpretations, and submit Giano proposals without approving them. On completion report counts, problems, costs and artifact links and pause any monitor. If active work stops before completion, explicitly say what stopped, why, and what remains; do not claim background monitoring unless it is actually active.
