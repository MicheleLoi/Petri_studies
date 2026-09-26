# Implementation and offline verification

This new package prepares 288 prospective Jev slots: Germany 160 and Switzerland 128, with sixteen balanced blocks containing all eighteen source–text cells. It does not modify or repeat an earlier collection. The deterministic shuffle seed is 2026092601. One worker sends one request at a time and retries within the current slot before continuing.

## Reused implementation

`code/main_runner.py` retains the prior extension's immutable attempt files, OS execution lock, hash checks, persisted three-attempt limit, recovery of saved responses, uncertain-attempt handling, retry timing, suspensions and cumulative budget checks. The Jev daily documentary launch/resume check follows the original US study. The actual public receipt, environment and frozen package must pass verification before the explicit execute command can collect data. Routine verify and all imports perform no inference.

`code/main_adapters.py` retains the US Jev score, legend, probability, consistency, identity and routing policy. The primary score is divided by four; confidence is not a strength rating. Missing or invalid auxiliary distributions preserve an otherwise usable primary score and are flagged without renormalization. An assessable inconsistency, changed legend, unaccepted identity or unexpected upstream-attempt count pauses collection. The transport has no automatic retries, redirects or provider fallback. It reads the existing local gateway credential only immediately before a send and excludes the credential from recorded request objects.

Two metadata corrections are prospective: an accepted score has category `usable`, and boolean gateway cost/attempt-count fields are rejected as numeric metadata. These do not change any of the 270 historical US Jev envelope assessments on scientific fields in the independent offline compatibility audit.

`code/budget.py` is unchanged from the completed extension. It scans historical requests, preserves uncertain-cost reserves, includes the Gemini EU premium, and reserves remaining permissible attempts before each block plus each individual send. A Jev attempt reserves EUR 0.01 unless a gateway-reported cost is available. Thus the maximum opening reserve for one complete block is EUR 0.54. The unchanged full ledger scan can add substantial local overhead; no cached accounting shortcut is used.

## Materials and analysis

`materials/ARGUMENTS.json` preserves the four European text strings and their provenance/hash fields from the completed extension. `materials/CASES.json` preserves all source labels and five source pairs, with the requested configuration set to Jev only. AfD denotes the party label actually used in the earlier extension. `materials/JEV_SPEC_US.json` is the historical US specification, retained as provenance for the same five anchor descriptions and score policy; its historical dates/status do not describe this new package. `materials/STATE_TEMPLATE.json` preserves the attribution-and-argument prefix. Topic substitution is the only question-instruction change. Every new state was checked against the corresponding frozen European GPT-4o user-message prefix before `Please provide:`.

`code/main_report.py` reports both panels, all eighteen cells, five pair interactions, fixed block halves 1–8 and 9–16, exact score frequencies, chronology, missingness, recoveries, cost and native Jev diagnostics. Illustrations are the first usable structured answer in planned order for each cell. Jev supplies no prose rationale. The report does not compute p-values, confidence intervals, equivalence verdicts or a calibrated model ranking. It refuses to run its real-data CLI before collection finishes, checks publication-before-request chronology, and creates a fresh output directory without overwriting an earlier report.

## Verification on 26 September 2026

The complete suite passed **25 offline tests** with real HTTP disabled. Tests cover balance/determinism and exact materials; native score and auxiliary diagnostics; invalid or ambiguous JSON; model/routing changes; retries and `Retry-After`; accepted-score non-repetition; exhausted and uncertain attempts across restart; saved-response recovery; persistent suspensions; ledger reserves and historical EU premium; OS locking; hash tampering; dated documentary evidence; and the public launch receipt gate.

A full synthetic rehearsal obtained **288/288** scores, generated both panels, all eighteen structured illustrations, the descriptive report, and both ratings/chronology plots. Every cell had sixteen scores and eight per fixed half. Known synthetic interactions were recovered, with the AfD–Junge Liberale difference fixed to zero and the other four interactions to 0.2. Both figures were visually inspected. Synthetic artifacts remain in the private preflight evidence directory and are excluded from scientific data. No live API call was used for these implementation checks.

Commands:

```text
python -B -m unittest discover -s code -p test_jev_europe.py -v
python -B code/main_rehearsal.py --out NEW_SYNTHETIC_DIRECTORY
```

The parent process supplies the human-readable protocol, fresh documentary evidence, tested environment, frozen plan/manifest, actual public registration and genuine launch receipt. This implementation note is not a publication or collection receipt.
