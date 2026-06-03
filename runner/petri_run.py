"""
petri_run.py — single entrypoint for source-attribution-bias-multipolity replication.

Phase A: skeleton. Handles CLI parsing, YAML loading, JSON Schema validation,
and Jinja2 template rendering. NO Petri API calls yet — those land in Phase A2
once the Petri version is pinned in requirements.lock (see plan §8).

Usage:
    python petri_run.py --polity uk --topic ai_regulation --dry-run
    python petri_run.py --polity de --topic carbon_tax --condition baseline --dry-run

Exit codes:
    0   — success (dry-run printed, or Phase A2+ run completed)
    1   — usage error
    2   — config not found
    3   — schema validation failed
    4   — template render failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jinja2
import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = RUNNER_DIR / "schema.json"
TEMPLATE_PATH = RUNNER_DIR / "template.j2"

VALID_POLITIES = ["de", "ch", "uk", "us", "it"]


def load_config(polity: str, topic: str) -> dict:
    """Load a YAML config from configs/<polity>/<topic>.yaml.

    Raises FileNotFoundError if the config does not exist.
    """
    config_path = REPO_ROOT / "configs" / polity / f"{topic}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}\n"
            f"Expected layout: configs/{polity}/{topic}.yaml\n"
            f"(For Phase A skeleton, no polity configs exist yet — "
            f"this is expected. Pass a config inline in tests.)"
        )
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def validate_config(config: dict) -> None:
    """Validate config dict against the JSON Schema. Raises ValidationError if invalid."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=config, schema=schema)


def render_seed_instruction(config: dict) -> str:
    """Render the Jinja2 template into the SEED_INSTRUCTION string.

    Phase B: byte-equivalent with DE/CH legacy scripts. The trailing whitespace
    is normalized in Python (not in Jinja2) because Jinja2 whitespace control
    around {% if %}{% endif %} blocks is too asymmetric to express the DE-vs-CH
    trailing difference (DE ends with \\n\\n, CH ends with \\n).
    """
    # Defaults
    render_config = dict(config)
    render_config.setdefault("include_auditor_communication_style", True)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_PATH.parent)),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        autoescape=False,
    )
    template = env.get_template(TEMPLATE_PATH.name)
    rendered = template.render(**render_config)

    # Normalize trailing newlines per legacy convention.
    # DE-style (with Auditor Communication Style section): ends with \n\n
    # CH-style (no Auditor section): ends with \n
    rendered = rendered.rstrip("\n")
    if render_config["include_auditor_communication_style"]:
        rendered += "\n\n"
    else:
        rendered += "\n"
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--polity", required=True, choices=VALID_POLITIES)
    parser.add_argument("--topic", required=True, help="Topic id (matches configs/<polity>/<topic>.yaml)")
    parser.add_argument(
        "--condition",
        default="all",
        help="Condition id to run, or 'all' (default). Phase A2+: selects which Petri seed step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered SEED_INSTRUCTION and exit. No model call. Works in Phase A.",
    )
    parser.add_argument(
        "--reproduce",
        action="store_true",
        help="(Phase D+) Verify byte-equivalence against a published .eval.",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.polity, args.topic)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    try:
        validate_config(config)
    except jsonschema.ValidationError as e:
        print(f"SCHEMA ERROR: {e.message}\n  at: {list(e.absolute_path)}", file=sys.stderr)
        return 3

    try:
        seed_instruction = render_seed_instruction(config)
    except jinja2.TemplateError as e:
        print(f"TEMPLATE ERROR: {e}", file=sys.stderr)
        return 4

    if args.dry_run:
        print(seed_instruction)
        return 0

    # Phase A2 hook — Petri integration will land here.
    print(
        "[Phase A skeleton — Petri integration deferred to A2]\n"
        f"Would run: polity={args.polity} topic={args.topic} condition={args.condition}\n"
        f"Config validated. Template renders to {len(seed_instruction)} chars.\n"
        f"Pass --dry-run to inspect the rendered SEED_INSTRUCTION.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
