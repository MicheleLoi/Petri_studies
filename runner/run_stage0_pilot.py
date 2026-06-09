"""run_stage0_pilot.py — reproducible recipe for the Stage-0 confabulation pilot.

Encodes the EXACT blocks run on 2026-06-09 (SID-20260609-105624) for the Stage-0
protocol-lock pilot of the confabulation study (see docs/confabulation_study_protocol.md
and PREREGISTRATION.md "Confabulation study"). All roles = Sonnet 4.6, UK carbon_tax,
arm = fresh_per_condition.

This file exists so the Stage-0 data-generating procedure is versioned, not ephemeral:
the original run was issued as an equivalent inline shell invocation; this script
reproduces it block-for-block. Re-runnable — each --repeat call saves .eval files
incrementally; runner/analyze_stage0.py dedups by file.

Requires ANTHROPIC_API_KEY in the environment. The caller injects it; it is NEVER
hard-coded here or committed. inspect_ai also auto-loads a .env from CWD if present.

Usage (PowerShell, key injected from the persistent user-scope env var):
    $env:ANTHROPIC_API_KEY = [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')
    python runner/run_stage0_pilot.py          # run all blocks
    python runner/run_stage0_pilot.py --dry    # print the planned invocations, run nothing

Blocks (auditor = target = judge = anthropic/claude-sonnet-4-6):
    quantization / medium : carbon_tax        baseline        x40   (H0b -> tau; doubles as the medium rung)
    positive control      : carbon_tax_strong baseline        x15   (H0a gate: strong - weak >= 0.15 ?)
                            carbon_tax_weak   baseline        x15
    confabulation blind   : carbon_tax        progressive_tt  x10   (canonical ratings, no probe)
                            carbon_tax        right_actor      x10
    confabulation probe   : carbon_tax        progressive_tt  x10   --probe (frozen self-report)
                            carbon_tax        right_actor      x10   --probe
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "petri_run.py"
MODEL = "anthropic/claude-sonnet-4-6"

# (topic, condition, repeat, probe)
BLOCKS = [
    ("carbon_tax",        "baseline",       40, False),
    ("carbon_tax_strong", "baseline",       15, False),
    ("carbon_tax_weak",   "baseline",       15, False),
    ("carbon_tax",        "progressive_tt", 10, False),
    ("carbon_tax",        "right_actor",    10, False),
    ("carbon_tax",        "progressive_tt", 10, True),
    ("carbon_tax",        "right_actor",    10, True),
]


def build_cmd(topic: str, cond: str, n: int, probe: bool) -> list[str]:
    cmd = [
        sys.executable, str(RUNNER),
        "--polity", "uk", "--topic", topic, "--arm", "fresh_per_condition",
        "--condition", cond, "--execute",
        "--auditor", MODEL, "--target", MODEL, "--judge", MODEL,
        "--repeat", str(n),
    ]
    if probe:
        cmd.append("--probe")
    return cmd


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true", help="Print the planned invocations and run nothing.")
    args = ap.parse_args(argv)

    for topic, cond, n, probe in BLOCKS:
        cmd = build_cmd(topic, cond, n, probe)
        print(f"\n==== BLOCK topic={topic} cond={cond} n={n} probe={probe} ====", flush=True)
        print("  " + " ".join(cmd), flush=True)
        if args.dry:
            continue
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print(f"BLOCK FAILED rc={rc} (topic={topic} cond={cond} probe={probe})", file=sys.stderr)
            return rc

    print("\n==== STAGE-0 PILOT COMPLETE ====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
