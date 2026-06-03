# Adding a Polity

Step-by-step protocol for adding a new polity (or extending an existing one) after the initial UK/US/IT roll-out.

> ⚠️ Phase A skeleton — to be expanded after the UK pilot establishes the exact ratification flow.

## Steps

1. **Define the source-coding ratification process.**
   - Identify the polity-specific entities that map to each of the 7 structural slots (`baseline`, `generic`, `progressive_tt`, `conservative_tt`, `green_actor`, `right_actor`, `neutral_institution`).
   - Recruit ≥1 human coder familiar with the polity's political landscape.
   - Document the criteria in `configs/<polity>/source_coding_ratified.yaml`.
   - Ratification = explicit human approval recorded in the YAML's frontmatter (signed/dated).

2. **Draft topic YAMLs** under `configs/<polity>/`. One file per topic (e.g., `ai_regulation.yaml`, `carbon_tax.yaml`, plus a polity-native fiscal topic).

3. **Validate locally:**
   ```bash
   python runner/petri_run.py --polity <new_polity> --topic <topic> --dry-run
   ```
   Verify the rendered SEED_INSTRUCTION makes sense.

4. **Pre-register:**
   - Commit the frozen design.
   - `git tag preregistered-<new_polity>-v1`
   - Push the tag.

5. **Run.**
   ```bash
   python runner/petri_run.py --polity <new_polity> --topic <topic> --condition baseline
   # ... etc for all 7 conditions
   ```

6. **Log:** every event in `lab_journal.md`, every code change as an MHC modlog entry in the linked workspace.

7. **Publish:** push `.eval` files to GitHub; update `evals/manifest.sha256`.

## Anti-patterns (do not do these)

- ❌ Editing `runner/petri_run.py` for a polity-specific tweak. If it's polity-specific, it goes in the YAML; if it's methodological, it goes in the runner AND requires a new pre-registration tag.
- ❌ Adding a new topic without updating `source_coding_ratified.yaml` first.
- ❌ Skipping the `--dry-run` review before consuming API tokens.
- ❌ Hand-editing a `.eval` file. They are output, not input — if a re-run is needed, do a re-run.
- ❌ Creating `study5_<topic>.py` for "a special case". The special case goes in YAML, or the runner is methodologically extended (with a new pre-registration tag).
