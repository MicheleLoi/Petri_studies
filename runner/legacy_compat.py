"""
legacy_compat.py — proof of byte-equivalence between the new runner+config
pipeline and the historical hardcoded SEED_INSTRUCTION strings in DE/CH scripts.

Phase B: verifies that configs/<polity>/<topic>.yaml + runner/template.j2
produces the same SEED_INSTRUCTION as a designated legacy script (e.g.,
~/Petri_studies/study4_carbon_tax_patched.py).

The legacy SEED_INSTRUCTION is extracted by regex (does NOT execute the legacy
script — avoids needing Petri/Inspect-AI installed).

Usage:
    python runner/legacy_compat.py --polity de --topic carbon_tax
    python runner/legacy_compat.py --polity de --topic carbon_tax --show-diff
    python runner/legacy_compat.py --polity de --topic carbon_tax --show-reprs

Exit codes:
    0 — MATCH ✓
    1 — usage error
    2 — legacy script not found
    3 — SEED_INSTRUCTION not found in legacy script
    4 — MISMATCH ✗
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from pathlib import Path

RUNNER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUNNER_DIR))
from petri_run import load_config, render_seed_instruction, validate_config  # noqa: E402

# Default location of the decommissioned legacy Python scripts (read-only archive).
# The original `~/Petri_studies/` was renamed to `~/Petri_studies/_archive/`
# on 2026-06-03 (workspace MOD-003 / Phase C). Override via env var LEGACY_DIR for
# unusual setups (CI, restored snapshot at non-default path).
LEGACY_DIR = Path(os.environ.get(
    "LEGACY_DIR",
    "C:/Users/loimi/Petri_studies/_archive",
))

# Mapping: (polity, topic) -> path to the canonical legacy script (within LEGACY_DIR)
LEGACY_SOURCES = {
    ("de", "carbon_tax"): "study4_carbon_tax_patched.py",
    ("ch", "carbon_tax"): "run_swiss_carbon_tax.py",
    # Future entries (Phase B continuation):
    # ("de", "ai_regulation"): "study4_ai_regulation_patched.py",
    # ("de", "ai_security"): "study4_ai_security_patched_v1.py",
    # ("de", "nuclear_energy"): "study4_nuclear_energy_C_patched.py",
    # ("de", "schuldenbremse_maintain"): "study4_debt_brake_maintain_patched.py",
    # ("de", "schuldenbremse_reform"): "study4_debt_brake_patched.py",
    # ("ch", "ai_security"): "run_swiss_AI_security.py",
    # ("ch", "nuclear_energy"): "run_swiss_nuclear_energy.py",
    # ("ch", "schuldenbremse_maintain"): "run_swiss_schuldenbremse_pro_maintain.py",
    # ("ch", "schuldenbremse_reform"): "run_swiss_schuldenbremse_pro_reform.py",
}


def extract_seed_instruction(script_path: Path) -> str:
    """Extract the SEED_INSTRUCTION constant from a legacy script via regex.

    Does NOT execute the script — avoids needing Petri/Inspect-AI installed.
    """
    text = script_path.read_text(encoding="utf-8")
    # Match: SEED_INSTRUCTION = """...""" (greedy across newlines)
    match = re.search(
        r'SEED_INSTRUCTION\s*=\s*"""(.*?)"""',
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError(f"No SEED_INSTRUCTION = \"\"\"...\"\"\" found in {script_path}")
    return match.group(1)


def _char_repr(s: str, prefix: str = "  ") -> str:
    """Show first/last 200 chars with explicit newlines for whitespace debugging."""
    head = s[:200].replace("\n", "\\n\n")
    tail = s[-200:].replace("\n", "\\n\n")
    return f"{prefix}HEAD: {head!r}\n{prefix}TAIL: {tail!r}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--polity", required=True, choices=["de", "ch"])
    parser.add_argument("--topic", required=True)
    parser.add_argument("--show-diff", action="store_true", help="Print unified diff on mismatch")
    parser.add_argument("--show-reprs", action="store_true", help="Print head/tail repr() for whitespace debug")
    parser.add_argument("--write-fixtures", action="store_true", help="Write expected/rendered to /tmp/ for external diff")
    args = parser.parse_args(argv)

    key = (args.polity, args.topic)
    if key not in LEGACY_SOURCES:
        print(f"ERROR: no legacy source mapped for {key}", file=sys.stderr)
        print(f"  Known pairs: {list(LEGACY_SOURCES)}", file=sys.stderr)
        return 1

    legacy_script = LEGACY_DIR / LEGACY_SOURCES[key]
    if not legacy_script.exists():
        print(f"ERROR: legacy script not found: {legacy_script}", file=sys.stderr)
        return 2

    print(f"Legacy source : {legacy_script}")
    try:
        expected = extract_seed_instruction(legacy_script)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    print(f"  -> {len(expected)} chars, {expected.count(chr(10))} newlines")

    config = load_config(args.polity, args.topic)
    validate_config(config)
    rendered = render_seed_instruction(config)
    print(f"Rendered from : configs/{args.polity}/{args.topic}.yaml")
    print(f"  -> {len(rendered)} chars, {rendered.count(chr(10))} newlines")

    if expected == rendered:
        print(f"\nMATCH [OK]  configs/{args.polity}/{args.topic}.yaml + runner reproduce the legacy SEED_INSTRUCTION byte-per-byte.")
        return 0

    print(f"\nMISMATCH [X]")
    print(f"  Expected length: {len(expected)}")
    print(f"  Rendered length: {len(rendered)}")
    print(f"  First differing char index: {next((i for i in range(min(len(expected), len(rendered))) if expected[i] != rendered[i]), 'tail-only diff')}")

    if args.show_reprs:
        print("\n--- EXPECTED ---")
        print(_char_repr(expected))
        print("\n--- RENDERED ---")
        print(_char_repr(rendered))

    if args.show_diff:
        print("\n--- UNIFIED DIFF (expected → rendered) ---")
        diff_lines = list(difflib.unified_diff(
            expected.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile="legacy SEED_INSTRUCTION",
            tofile="rendered SEED_INSTRUCTION",
            n=2,
        ))
        for line in diff_lines[:300]:
            sys.stdout.write(line)

    if args.write_fixtures:
        Path("/tmp/expected.txt").write_text(expected, encoding="utf-8")
        Path("/tmp/rendered.txt").write_text(rendered, encoding="utf-8")
        print("\n  Fixtures written: /tmp/expected.txt /tmp/rendered.txt")

    return 4


if __name__ == "__main__":
    sys.exit(main())
