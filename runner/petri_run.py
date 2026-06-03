"""
petri_run.py — single entrypoint for source-attribution-bias-multipolity replication.

Modes (cumulative — each later mode subsumes the earlier):
    --dry-run    : render SEED_INSTRUCTION and exit. No Petri required.
    (no flag)    : validate config + report. No Petri call. Skeleton info mode.
    --execute    : Phase A2+ — actually run Petri auditor_agent + alignment_judge
                   and save .eval files. Requires Petri SDK + ANTHROPIC_API_KEY.
    --reproduce  : Phase D+ — verify byte-equivalence against a published .eval.
                   NOT YET IMPLEMENTED.

Usage examples:
    # No Petri needed:
    python petri_run.py --polity de --topic carbon_tax --dry-run

    # Phase A2 execute (requires Petri + ANTHROPIC_API_KEY):
    python petri_run.py --polity uk --topic ai_regulation --execute \\
        --auditor anthropic/claude-sonnet-4-20250514 \\
        --target anthropic/claude-sonnet-4-20250514 \\
        --judge anthropic/claude-sonnet-4-20250514

Exit codes:
    0   success
    1   usage error
    2   config not found
    3   schema validation failed
    4   template render failed
    5   --execute requested but Petri SDK not installed
    6   execution / API error
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import warnings
from pathlib import Path

import jinja2
import jsonschema
import yaml

# petri 0.1.0 emits DeprecationWarnings at import time about inspect_ai.event.*
# moved imports (introduced in inspect_ai 0.3.137). These are warnings, not
# errors — petri still works. Suppress them via both the warnings filter (for
# the rare petri call that uses warnings.warn) AND a stderr redirect during the
# imports themselves (petri seems to print directly). Remove when petri 0.1.1+
# uses the new import paths.
warnings.filterwarnings(
    "ignore",
    message=r".*has been moved to 'inspect_ai\.event\..*",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = RUNNER_DIR / "schema.json"
TEMPLATE_PATH = RUNNER_DIR / "template.j2"
SHARED_CONFIGS = REPO_ROOT / "configs" / "_shared"

VALID_POLITIES = ["de", "ch", "uk", "us", "it"]

# Deferred Petri imports — runner imports cleanly even when Petri is absent
# (pytest, --dry-run, validation-only mode). The flag is checked before --execute.
# stderr redirect silences petri 0.1.0's import-time deprecation prints (see
# the warnings filter above for the matching rationale).
_HAS_PETRI = False
_PETRI_IMPORT_ERROR: Exception | None = None
_petri_import_chatter = io.StringIO()
try:
    with contextlib.redirect_stderr(_petri_import_chatter):
        from petri.solvers.auditor_agent import auditor_agent
        from petri.scorers.judge import alignment_judge
        from inspect_ai import Task, eval as _inspect_eval
        from inspect_ai.dataset import Sample
        from inspect_ai.model import get_model
    _HAS_PETRI = True
except ImportError as _exc:
    _PETRI_IMPORT_ERROR = _exc


# --- Loading / validation / rendering --------------------------------------

def load_config(polity: str, topic: str) -> dict:
    """Load a YAML config from configs/<polity>/<topic>.yaml."""
    config_path = REPO_ROOT / "configs" / polity / f"{topic}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found: {config_path}\n"
            f"Expected layout: configs/{polity}/{topic}.yaml"
        )
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def load_judge_dimensions() -> dict:
    """Load polity-invariant judge dimensions from configs/_shared/judge_dimensions.yaml."""
    path = SHARED_CONFIGS / "judge_dimensions.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_config(config: dict) -> None:
    """Validate config dict against the JSON Schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=config, schema=schema)


def render_seed_instruction(config: dict) -> str:
    """Render the Jinja2 template into the SEED_INSTRUCTION string.

    Trailing whitespace normalized in Python (not in Jinja2) because Jinja2
    whitespace control around {% if %}{% endif %} blocks is too asymmetric to
    express the DE-vs-CH trailing difference (DE ends \\n\\n, CH ends \\n).
    """
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

    rendered = rendered.rstrip("\n")
    if render_config["include_auditor_communication_style"]:
        rendered += "\n\n"
    else:
        rendered += "\n"
    return rendered


# --- Phase A2: Petri execution + harness integration -----------------------

def _eval_output_dir(polity: str, topic: str, condition: str) -> Path:
    """Path where .eval files for this polity/topic/condition land."""
    return REPO_ROOT / "evals" / polity / topic / condition


def execute_petri(
    seed_instruction: str,
    judge_dimensions: dict,
    auditor_model: str,
    target_model: str,
    judge_model: str,
    output_dir: Path,
    max_turns: int = 15,
):
    """Run Petri eval and save .eval log file. Phase A2 integration.

    Returns whatever inspect_ai.eval returns (typically a list of EvalLog objects).
    Raises RuntimeError if Petri SDK is not available.
    """
    if not _HAS_PETRI:
        raise RuntimeError(
            f"Petri SDK not available: {_PETRI_IMPORT_ERROR}\n"
            f"Install: pip install -r runner/requirements.lock"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    task_obj = Task(
        dataset=[Sample(input=seed_instruction)],
        solver=auditor_agent(max_turns=max_turns),
        scorer=alignment_judge(dimensions=judge_dimensions),
    )

    return _inspect_eval(
        task_obj,
        model_roles={
            "auditor": get_model(auditor_model),
            "target": get_model(target_model),
            "judge": get_model(judge_model),
        },
        log_dir=str(output_dir),
    )


def _resolve_workspace_path() -> Path | None:
    """Find the MHC workspace for harness ledger calls.

    Priority: env var MHC_WORKSPACE_PATH; fallback canonical local path; else None.
    """
    env_path = os.environ.get("MHC_WORKSPACE_PATH")
    if env_path and Path(env_path, "mhc_harness_client.py").exists():
        return Path(env_path)
    canonical = Path("C:/Users/loimi/switchdrive/CURRENTLY WORKING ON/AI - assisted papers/Epistemic constitutional AI")
    if (canonical / "mhc_harness_client.py").exists():
        return canonical
    return None


def register_eval_in_harness(eval_path: Path, polity: str, topic: str, condition: str) -> dict | None:
    """Register a generated .eval file in the MHC harness ledger.

    Returns the harness response dict, or None if the workspace cannot be located.
    Failures are logged but do not raise — the .eval is preserved regardless.
    """
    workspace = _resolve_workspace_path()
    if workspace is None:
        print(
            f"[harness] No MHC workspace found (set MHC_WORKSPACE_PATH); "
            f"skipping placement_log for {eval_path}",
            file=sys.stderr,
        )
        return None

    try:
        sys.path.insert(0, str(workspace))
        # Local import — only when actually called, to avoid side-effects
        from mhc_harness_client import register, get_session  # type: ignore[import-not-found]

        sid = (get_session() or {}).get("sid")
        result = register(
            artifact=str(eval_path),
            type=f"eval_file:{polity}:{topic}:{condition}",
            sid=sid,
        )
        print(f"[harness] register {eval_path.name} -> {result.get('status')}", file=sys.stderr)
        return result
    except Exception as e:
        print(f"[harness] register failed for {eval_path}: {e}", file=sys.stderr)
        return None


# --- CLI ------------------------------------------------------------------

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
        help="Condition id label for output organization (default 'all'). Petri runs all 7 in sequence within one auditor_agent call.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered SEED_INSTRUCTION and exit. No Petri required.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="(Phase A2) Run Petri eval and save .eval file. Requires Petri SDK + ANTHROPIC_API_KEY.",
    )
    parser.add_argument(
        "--reproduce",
        action="store_true",
        help="(Phase D+) Verify byte-equivalence against a published .eval. NOT YET IMPLEMENTED.",
    )
    parser.add_argument(
        "--auditor",
        default=None,
        help="Petri auditor model id (e.g. 'anthropic/claude-sonnet-4-20250514'). Required when --execute.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Petri target model id. Required when --execute.",
    )
    parser.add_argument(
        "--judge",
        default=None,
        help="Petri judge model id. Required when --execute.",
    )
    parser.add_argument(
        "--max-turns",
        type=int, default=15,
        help="Petri auditor max_turns (default: 15, matches legacy DE/CH)",
    )
    args = parser.parse_args(argv)

    # Load + validate + render — always (cheap, fast)
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

    # --- Mode dispatch ---

    if args.dry_run:
        print(seed_instruction)
        return 0

    if args.reproduce:
        print("ERROR: --reproduce not yet implemented (Phase D+)", file=sys.stderr)
        return 1

    if not args.execute:
        # Skeleton info mode: validate + report, no model call
        print(
            f"[skeleton mode - pass --execute to run Petri, or --dry-run to preview]\n"
            f"  Polity/topic        : {args.polity}/{args.topic}\n"
            f"  Schema validated    : OK\n"
            f"  Template renders to : {len(seed_instruction)} chars / {seed_instruction.count(chr(10))} newlines\n"
            f"  Petri SDK available : {_HAS_PETRI}",
            file=sys.stderr,
        )
        return 0

    # --- --execute (Phase A2 Petri integration) ---

    if not _HAS_PETRI:
        print(
            f"ERROR: --execute requires Petri SDK. Import error: {_PETRI_IMPORT_ERROR}\n"
            f"Install: pip install -r runner/requirements.lock",
            file=sys.stderr,
        )
        return 5

    missing = [name for name, val in [("--auditor", args.auditor), ("--target", args.target), ("--judge", args.judge)] if not val]
    if missing:
        print(
            f"ERROR: --execute requires {', '.join(missing)}. No default model is wired "
            f"(Phase D pre-registration concern).",
            file=sys.stderr,
        )
        return 1

    judge_dimensions = load_judge_dimensions()
    output_dir = _eval_output_dir(args.polity, args.topic, args.condition)

    print(
        f"[execute] polity={args.polity} topic={args.topic} condition={args.condition}\n"
        f"  Models : auditor={args.auditor}\n"
        f"           target ={args.target}\n"
        f"           judge  ={args.judge}\n"
        f"  Output : {output_dir}\n"
        f"  Max turns        : {args.max_turns}\n"
        f"  Judge dimensions : {list(judge_dimensions.keys())}",
        file=sys.stderr,
    )

    try:
        execute_petri(
            seed_instruction=seed_instruction,
            judge_dimensions=judge_dimensions,
            auditor_model=args.auditor,
            target_model=args.target,
            judge_model=args.judge,
            output_dir=output_dir,
            max_turns=args.max_turns,
        )
    except Exception as e:
        print(f"EXECUTION ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 6

    # Locate and register newly produced .eval files
    eval_files = sorted(output_dir.glob("*.eval"))
    if not eval_files:
        print(f"[execute] No .eval files produced in {output_dir}", file=sys.stderr)
    else:
        print(f"[execute] Produced {len(eval_files)} .eval file(s):", file=sys.stderr)
        for ef in eval_files[-3:]:
            print(f"  {ef.name}", file=sys.stderr)
            register_eval_in_harness(ef, args.polity, args.topic, args.condition)

    return 0


if __name__ == "__main__":
    sys.exit(main())
