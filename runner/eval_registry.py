"""eval_registry.py - scan evals/ and append entries to lab_journal.md.

Idempotent: each .eval's eval_id is the identity key. If an eval_id already
appears in lab_journal.md, the entry is skipped. Re-runnable safely.

Scope: only scans `evals/`, NOT `_archive/` (legacy historical data is reference,
not part of the new framework's lab_journal).

Usage:
    python runner/eval_registry.py            # scan + append new entries
    python runner/eval_registry.py --dry-run  # show what WOULD be added, no write
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_ROOT = REPO_ROOT / "evals"
LAB_JOURNAL = REPO_ROOT / "lab_journal.md"
WORKSPACE_PATH = Path(
    "C:/Users/loimi/switchdrive/CURRENTLY WORKING ON/AI - assisted papers/"
    "Epistemic constitutional AI"
)


def extract_eval_metadata(eval_path: Path) -> dict:
    """Open a .eval (zip), return dict with all the metadata we want to log."""
    with zipfile.ZipFile(eval_path) as z:
        with z.open("header.json") as f:
            header = json.load(f)
        try:
            with z.open("summaries.json") as f:
                summaries = json.load(f)
        except KeyError:
            summaries = None

    ev = header.get("eval", {})
    eval_id = ev.get("eval_id", "unknown")
    created = ev.get("created", "")
    task_name = ev.get("task", "")
    status = header.get("status", "unknown")

    model_roles = ev.get("model_roles", {}) or {}
    auditor = (model_roles.get("auditor", {}) or {}).get("model", "?")
    target = (model_roles.get("target", {}) or {}).get("model", "?")
    judge = (model_roles.get("judge", {}) or {}).get("model", "?")

    rel = eval_path.relative_to(EVALS_ROOT)
    polity = rel.parts[0] if len(rel.parts) >= 1 else "?"

    fname = eval_path.stem
    topic = "?"
    condition = "?"

    # Convention 1 (legacy/manual): filename prefix `<condition_label>__<rest>.eval`
    if "__" in fname:
        condition = fname.split("__")[0]

    # Convention 2 (new petri_run.py task_name): `<polity>_<topic>_<condition>`
    # task_name is set by petri_run.py to args.polity + "_" + args.topic + "_" + args.condition
    # Topic can have underscores (carbon_tax). Heuristic: split off leading polity,
    # remaining = topic_..._condition where condition often starts with "trial_".
    if task_name and task_name not in ("task", "none/none", ""):
        parts = task_name.split("_")
        if parts and parts[0] == polity and len(parts) >= 2:
            rest = "_".join(parts[1:])
            m = re.search(r"^(.+?)_(trial_.*)$", rest)
            if m:
                topic = m.group(1)
                condition = m.group(2)
            else:
                topic = rest

    scores: dict = {}
    total_time = None
    token_usage: dict = {}
    if summaries and isinstance(summaries, list) and summaries:
        sample = summaries[0]
        sample_scores = sample.get("scores", {}) or {}
        for scorer_data in sample_scores.values():
            val = scorer_data.get("value", {})
            if isinstance(val, dict):
                for k, v in val.items():
                    scores[k] = v
        total_time = sample.get("total_time")
        token_usage = sample.get("model_usage", {}) or {}

    return {
        "eval_id": eval_id,
        "created": created,
        "polity": polity,
        "topic": topic,
        "condition": condition,
        "task_name": task_name,
        "status": status,
        "auditor": auditor,
        "target": target,
        "judge": judge,
        "scores": scores,
        "total_time": total_time,
        "token_usage": token_usage,
        "rel_path": str(rel).replace("\\", "/"),
    }


def existing_eval_ids(journal_text: str) -> set[str]:
    """Find eval_ids already cited in lab_journal."""
    return set(re.findall(r"eval_id=([A-Za-z0-9]+)", journal_text))


def fmt_tokens(usage: dict) -> str:
    """Sum total tokens across model roles."""
    total_in = 0
    total_out = 0
    for role_data in usage.values():
        total_in += role_data.get("input_tokens", 0)
        total_out += role_data.get("output_tokens", 0)
    if total_in + total_out == 0:
        return "n/a"
    return f"{total_in}in/{total_out}out"


def format_entry(meta: dict, sid: str = "UNKNOWN_SID") -> str:
    scores_str = (
        ", ".join(f"{k}={v}" for k, v in meta["scores"].items())
        or "none"
    )
    time_str = f"{meta['total_time']:.0f}s" if meta["total_time"] else "n/a"
    tokens_str = fmt_tokens(meta["token_usage"])
    return (
        f"\n"
        f"## [{meta['created']}] [{sid}] [eval_saved]\n"
        f"**Polity:** {meta['polity']}\n"
        f"**Topic:** {meta['topic']}\n"
        f"**Condition:** {meta['condition']}\n"
        f"**Files:** evals/{meta['rel_path']}\n"
        f"**Notes:** eval_id={meta['eval_id']}; task={meta['task_name']}; "
        f"status={meta['status']}; auditor={meta['auditor']}; "
        f"target={meta['target']}; judge={meta['judge']}; "
        f"total_time={time_str}; tokens={tokens_str}; scores: {scores_str}\n"
    )


def find_current_sid() -> str:
    """Read current SID from workspace .mhc-config.json if accessible."""
    cfg_path = WORKSPACE_PATH / ".mhc-config.json"
    if not cfg_path.exists():
        return "UNKNOWN_SID"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return cfg.get("current_session", {}).get("id", "UNKNOWN_SID")
    except Exception:
        return "UNKNOWN_SID"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be appended, do not modify lab_journal.md")
    args = parser.parse_args(argv)

    if not LAB_JOURNAL.exists():
        print(f"lab_journal.md not found at {LAB_JOURNAL}", file=sys.stderr)
        return 1

    journal = LAB_JOURNAL.read_text(encoding="utf-8")
    seen = existing_eval_ids(journal)

    eval_files = sorted(EVALS_ROOT.rglob("*.eval")) if EVALS_ROOT.exists() else []
    if not eval_files:
        print("No .eval files found.", file=sys.stderr)
        return 0

    sid = find_current_sid()
    new_entries: list[str] = []
    skipped = 0

    for ef in eval_files:
        try:
            meta = extract_eval_metadata(ef)
        except Exception as e:
            print(f"[error] cannot read {ef.name}: {e}", file=sys.stderr)
            continue
        if meta["eval_id"] in seen:
            skipped += 1
            continue
        entry = format_entry(meta, sid)
        new_entries.append(entry)
        print(
            f"[new] {meta['eval_id']} -> "
            f"{meta['polity']}/{meta['topic']}/{meta['condition']} "
            f"status={meta['status']}",
            file=sys.stderr,
        )

    if not new_entries:
        print(
            f"No new evals (scanned {len(eval_files)}, all already in journal).",
            file=sys.stderr,
        )
        return 0

    if args.dry_run:
        print(f"--- DRY-RUN: would append {len(new_entries)} entries ---",
              file=sys.stderr)
        for e in new_entries:
            print(e)
        return 0

    new_text = journal.rstrip() + "\n" + "".join(new_entries) + "\n"
    LAB_JOURNAL.write_text(new_text, encoding="utf-8")
    print(
        f"Appended {len(new_entries)} entries to lab_journal.md "
        f"(skipped {skipped} already-tracked).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
