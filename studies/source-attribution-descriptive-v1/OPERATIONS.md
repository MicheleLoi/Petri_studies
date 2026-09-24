# Publication and collection

The author selected the existing public repository https://github.com/MicheleLoi/Petri_studies. The package belongs under `studies/source-attribution-descriptive-v1/`; the historical root preregistration and previous experiments remain intact.

1. Verify the public package, review the new public diff and any unpublished commits, then publish the exact version on GitHub with an identifiable release/tag. Record the actual commit, release URL, server publication time and manifest SHA-256. Local timestamps are not substitutes for that event. Immutable release assets may be used as an additional safeguard.
2. Check model identifiers, service/catalog availability, tariffs and Jev documentation on the actual collection date. Do not silently substitute a model. Prior successful access does not guarantee future availability. Record the checks without changing the fixed scientific inputs.
3. Record the author's actual launch instruction and real publication details in a private `launch-record.json`. No placeholder is authorization or evidence of publication.
4. Execute the code from this exact public package with `--study-root` pointing to the private study-design directory. That preserves the existing cumulative cost ledger and keeps raw responses private. Never start a parallel runner or clear an operating-system lock to force access.

Offline verification (from this package directory):

```powershell
python -B verify_manifest.py
python -B code/main_runner.py verify --package .
python -B -m unittest discover -s code -p "test_*.py" -v
```

Tests prohibit real HTTP sends. Run tests from a writable directory; their temporary files are placed under its `tmp-main-tests/` directory. Dependencies and Python version are recorded in ENVIRONMENT.json. Actual execution checks them against the verified environment.

The private launch record requires these fields: `manifest_sha256`, `registration_reference`, `registered_utc`, `visibility`, `author_launch_instruction`, `jev_presumed_model` (`jev-1.13.0`), `jev_version_recheck_utc` and `jev_version_evidence`. It must use this public manifest's digest, not the earlier private manifest's digest. The Jev recheck must be on the actual launch/resume UTC date.

The collector command is `python -B code/main_runner.py execute --package . --study-root <private-study-design-directory> --launch-record <private-launch-record>`. Angle-bracket paths must be replaced by actual private paths; they are not runnable examples. Raw data go to `runs/registered-study-v1/` under the private study root. Report with `code/main_report.py --package . --run <private-run-directory> --out <new-private-report-directory>`.

The fixed design uses up to three total sends per slot, preserves uncertain attempts and costs, and suspends affected models for the recorded version/configuration/schema conditions. Resumption never repeats an already saved request as the same attempt. The runner checks the existing project cost total before every block and send, with advance notice required before a projected EUR 100. Estimates and reserves are not invoices. Keep the private study root unchanged when resuming.

Credentials are read at runtime: OPENAI_API_KEY and ANTHROPIC_API_KEY from the environment; the Vercel key from the current user's `.config/source-attribution/secrets.env`; Google ADC from the current user's `.gcloud-adc/application_default_credentials.json`. Credential values must never be committed. The preserved original Vertex endpoint uses the original project's access configuration; an independent replication must document its own configuration rather than silently call a substituted model or region.
