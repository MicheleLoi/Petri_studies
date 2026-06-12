"""calibration_ledger.py — build the STEP-0 calibration ledger from E1 .eval files.

Reads every ai_regulation_e1[/_wredit] .eval under evals/de/, and for each one
computes the per-model token usage + as-billed AND uncached-equivalent cost,
extracts the target's strength_rating (and, for probe sessions, the self-report
JSON), classifies eval-type (behavioral / probe / winrate) and cell, and records
the auditor model (for the Haiku-vs-Sonnet auditor-contrast arm).

Outputs:
  - evals/de/_calibration_ledger.csv   (one row per eval)
  - a printed SUMMARY: per-eval-type cost (mean/min/max), per-model cost share,
    and the c0 blind-rating REGIME (raw multiset + grid + FLAT/QUANTIZED/WANDER).

Reference prices (USD per MTok) — VERIFY before trusting money figures (the program's
own thesis is that unverified numbers mislead). Matches calibration_pilot_spec.md s3a.
  SONNET 4.5 : in 3.00 / out 15.00      HAIKU 4.5 : in 1.00 / out 5.00
  cache write = 1.25x input (5-min TTL) ; cache read = 0.10x input ; thinking billed as output.

Usage:
    python runner/calibration_ledger.py            # scan + write CSV + print summary
    python runner/calibration_ledger.py --no-write # summary only, do not write CSV
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DE = REPO_ROOT / "evals" / "de"
LEDGER_CSV = EVALS_DE / "_calibration_ledger.csv"

PRICES = {  # USD per token (per-MTok / 1e6)
    "sonnet": {"in": 3.00 / 1e6, "out": 15.00 / 1e6},
    "haiku":  {"in": 1.00 / 1e6, "out": 5.00 / 1e6},
}
CACHE_WRITE_MULT = 1.25  # 5-min TTL
CACHE_READ_MULT = 0.10


def price_for(model: str) -> dict:
    m = model.lower()
    if "sonnet" in m:
        return PRICES["sonnet"]
    if "haiku" in m:
        return PRICES["haiku"]
    raise ValueError(f"No price for model {model!r} (extend PRICES).")


def short_model(model: str) -> str:
    m = model.lower()
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return model


def cost_asbilled(u: dict, p: dict) -> float:
    return (
        u.get("input_tokens", 0) * p["in"]
        + u.get("input_tokens_cache_write", 0) * p["in"] * CACHE_WRITE_MULT
        + u.get("input_tokens_cache_read", 0) * p["in"] * CACHE_READ_MULT
        + u.get("output_tokens", 0) * p["out"]
    )


def cost_uncached(u: dict, p: dict) -> float:
    total_in = (
        u.get("input_tokens", 0)
        + u.get("input_tokens_cache_write", 0)
        + u.get("input_tokens_cache_read", 0)
    )
    return total_in * p["in"] + u.get("output_tokens", 0) * p["out"]


def read_eval(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        header = json.load(z.open("header.json"))
        summaries = json.load(z.open("summaries.json"))
        sample_names = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        sample = json.load(z.open(sample_names[0])) if sample_names else {}
    return header, summaries, sample


def extract_ratings(sample: dict) -> tuple[float | None, dict | None]:
    """Return (strength_rating, probe_json). The first assistant message holds the
    blind rating; a probe session has a second assistant message with the self-report."""
    rating = None
    probe = None
    for m in sample.get("messages", []):
        if m.get("role") != "assistant":
            continue
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
        if rating is None:
            mm = re.search(r'"strength_rating"\s*:\s*([0-9]*\.?[0-9]+)', c)
            if mm:
                rating = float(mm.group(1))
        if probe is None and "source_effect_direction" in c:
            d = re.search(r'"source_effect_direction"\s*:\s*"(\w+)"', c)
            mag = re.search(r'"source_effect_magnitude"\s*:\s*(-?[0-9]*\.?[0-9]+)', c)
            pred = re.search(r'"predicted_rating_no_source"\s*:\s*([0-9]*\.?[0-9]+)', c)
            probe = {
                "dir": d.group(1) if d else None,
                "mag": float(mag.group(1)) if mag else None,
                "pred_no_source": float(pred.group(1)) if pred else None,
            }
    return rating, probe


def classify(topic: str, condition: str, is_probe: bool) -> tuple[str, str]:
    """Return (eval_type, cell)."""
    # Argument-quality sweep / positive controls: topic = ai_regulation_e1_<tag>.
    # endswith with the leading underscore disambiguates 'strong' from 'verystrong'.
    for tag, cell in [("veryweak", "PC-vweak"), ("weak", "PC-weak"), ("mediocre", "PC-mediocre"),
                      ("verystrong", "PC-vstrong"), ("strong", "PC-strong")]:
        if topic.endswith("_" + tag):
            return "poscontrol", cell
    if "wredit" in topic:
        etype = "winrate"
    elif is_probe:
        etype = "probe"
    else:
        etype = "behavioral"
    cell_map = {
        ("behavioral", "c0"): "B-rep", ("behavioral", "c4"): "B-ceil",
        ("behavioral", "c2"): "B-hp-against", ("behavioral", "c1"): "B-on",
        ("behavioral", "c3"): "B-c3",
        ("probe", "c4"): "P-ceil", ("probe", "c0"): "P-rep",
        ("winrate", "c0"): "W-c0", ("winrate", "c4"): "W-c4",
    }
    return etype, cell_map.get((etype, condition), f"{etype}:{condition}")


def row_for(path: Path) -> dict | None:
    header, summaries, sample = read_eval(path)
    ev = header.get("eval", {})
    status = header.get("status", "unknown")
    task = ev.get("task", "")
    roles = ev.get("model_roles", {}) or {}
    aud = (roles.get("auditor", {}) or {}).get("model", "?")
    tgt = (roles.get("target", {}) or {}).get("model", "?")
    jdg = (roles.get("judge", {}) or {}).get("model", "?")

    # task = de_<topic>_<condition>; topic may contain underscores, condition is the last token.
    body = task[len("de_"):] if task.startswith("de_") else task
    condition = body.rsplit("_", 1)[-1] if "_" in body else body
    topic = body[: -(len(condition) + 1)] if condition and body.endswith("_" + condition) else body

    s0 = summaries[0] if summaries else {}
    usage = s0.get("model_usage", {}) or {}
    rating, probe = extract_ratings(sample)
    is_probe = probe is not None
    etype, cell = classify(topic, condition, is_probe)

    # VALIDITY: a usable behavioral/winrate eval must have a target rating; a probe
    # must also have the self-report. No target usage => target never ran (degenerate).
    target_usage = next((u for mdl, u in usage.items() if "sonnet" in mdl.lower()), None)
    valid = (status == "success") and (target_usage is not None) and (rating is not None)
    if is_probe:
        valid = valid and (probe.get("dir") is not None)

    per_model = {}
    asbilled = 0.0
    uncached = 0.0
    for mdl, u in usage.items():
        p = price_for(mdl)
        ab = cost_asbilled(u, p)
        un = cost_uncached(u, p)
        per_model[short_model(mdl)] = {"usage": u, "asbilled": ab, "uncached": un}
        asbilled += ab
        uncached += un

    # Per-ROLE cost from events. model_usage is keyed by MODEL, so it cannot split
    # target from auditor/judge when they share a model (the all-Sonnet auditor-contrast
    # runs). Events carry a 'role' that reliably isolates the target from the rest.
    role_cost: dict[str, float] = {}
    for e in sample.get("events", []):
        if e.get("event") != "model":
            continue
        u = (e.get("output", {}) or {}).get("usage", {}) or {}
        try:
            p = price_for(e.get("model", ""))
        except ValueError:
            continue
        rl = e.get("role", "?")
        role_cost[rl] = role_cost.get(rl, 0.0) + cost_asbilled(u, p)
    role_total = sum(role_cost.values())
    tgt_event = role_cost.get("target", 0.0)

    return {
        "eval_id": ev.get("eval_id", "?"),
        "created": ev.get("created", ""),
        "file": path.name,
        "topic": topic,
        "condition": condition,
        "eval_type": etype,
        "cell": cell,
        "aud": short_model(aud),
        "tgt": short_model(tgt),
        "jdg": short_model(jdg),
        "status": status,
        "valid": valid,
        "rating": rating,
        "probe_dir": (probe or {}).get("dir"),
        "probe_mag": (probe or {}).get("mag"),
        "probe_pred_no_source": (probe or {}).get("pred_no_source"),
        "asbilled_usd": round(asbilled, 6),
        "uncached_usd": round(uncached, 6),
        "target_cost_share": round(tgt_event / role_total, 4) if role_total else None,
        "target_event_usd": round(tgt_event, 6),
        "orch_event_usd": round(role_total - tgt_event, 6),
        "per_model": per_model,
        "scores": {k: v for sc in (s0.get("scores", {}) or {}).values()
                   for k, v in (sc.get("value", {}) or {}).items()},
        "total_time": s0.get("total_time"),
    }


def regime(c0_ratings: list[float]) -> str:
    if not c0_ratings:
        return "n/a"
    distinct = sorted(set(c0_ratings))
    if len(distinct) == 1:
        return f"FLAT (all {len(c0_ratings)} = {distinct[0]})"
    spread = max(distinct) - min(distinct)
    grid = ATTRACTOR = {0.60, 0.62, 0.65, 0.68}
    on_grid = all(r in grid for r in distinct)
    label = "QUANTIZED" if (len(distinct) <= 3 and on_grid) else "WANDER"
    return f"{label} (distinct={distinct}, spread={round(spread, 3)})"


def fmt_band(vals: list[float]) -> str:
    if not vals:
        return "n/a"
    if len(vals) == 1:
        return f"${vals[0]:.4f} (n=1)"
    return (f"mean=${statistics.mean(vals):.4f} "
            f"[{min(vals):.4f}–{max(vals):.4f}] n={len(vals)} "
            f"sd=${statistics.pstdev(vals):.4f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-write", action="store_true", help="Print summary only; do not write the CSV.")
    args = ap.parse_args(argv)

    files = sorted(p for p in EVALS_DE.glob("*.eval")
                   if "ai_regulation_e1" in p.name or "ai-regulation-e1" in p.name)
    if not files:
        print("No E1 .eval files found under evals/de/.", file=sys.stderr)
        return 0

    rows = []
    for f in files:
        try:
            rows.append(row_for(f))
        except Exception as e:
            print(f"[error] {f.name}: {type(e).__name__}: {e}", file=sys.stderr)

    valid = [r for r in rows if r["valid"]]
    invalid = [r for r in rows if not r["valid"]]

    if not args.no_write:
        cols = ["eval_id", "created", "file", "topic", "condition", "eval_type", "cell",
                "aud", "tgt", "jdg", "status", "valid", "rating", "probe_dir", "probe_mag",
                "probe_pred_no_source", "asbilled_usd", "uncached_usd", "target_cost_share", "total_time"]
        with open(LEDGER_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"Wrote {LEDGER_CSV} ({len(rows)} rows).\n")

    print("=" * 72)
    print(f"CALIBRATION LEDGER SUMMARY — {len(valid)} valid / {len(invalid)} invalid eval(s)")
    print("=" * 72)

    for etype in ("behavioral", "winrate", "probe", "poscontrol"):
        sub = [r for r in valid if r["eval_type"] == etype]
        print(f"\n[{etype}] n={len(sub)}")
        print(f"  as-billed/eval : {fmt_band([r['asbilled_usd'] for r in sub])}")
        print(f"  uncached/eval  : {fmt_band([r['uncached_usd'] for r in sub])}")
        by_cell: dict[str, list] = {}
        for r in sub:
            by_cell.setdefault(r["cell"], []).append(r)
        for cell, rs in sorted(by_cell.items()):
            shares = [r["target_cost_share"] for r in rs if r["target_cost_share"] is not None]
            avg_share = f"{statistics.mean(shares)*100:.0f}%" if shares else "n/a"
            ratings = [r["rating"] for r in rs if r["rating"] is not None]
            print(f"    {cell:<14} n={len(rs):<2} {fmt_band([r['asbilled_usd'] for r in rs])} | target {avg_share} | ratings {sorted(ratings)}")

    # Role-based cost share (from event roles — valid even for all-Sonnet auditor-contrast runs)
    tgt_tot = sum(r["target_event_usd"] for r in valid)
    orch_tot = sum(r["orch_event_usd"] for r in valid)
    den = (tgt_tot + orch_tot) or 1.0
    print(f"\n[cost share, role-based] target {tgt_tot/den*100:.0f}%  |  auditor+judge {orch_tot/den*100:.0f}%")

    # c0 blind-rating regime (behavioral B-rep only), split by auditor for the contrast arm
    brep = [r for r in valid if r["cell"] == "B-rep"]
    c0r = [r["rating"] for r in brep]
    print(f"\n[c0 B-rep regime] n={len(c0r)} ratings={sorted(c0r)}")
    print(f"  -> {regime(c0r)}")
    for aud in ("haiku", "sonnet"):
        sub = [r["rating"] for r in brep if r["aud"] == aud]
        if sub:
            print(f"  aud={aud}: n={len(sub)} ratings={sorted(sub)} mean={statistics.mean(sub):.3f}")

    # H0a positive-control gate (only if strong/weak evals are present)
    pc_strong = [r["rating"] for r in valid if r["cell"] == "PC-strong" and r["rating"] is not None]
    pc_weak = [r["rating"] for r in valid if r["cell"] == "PC-weak" and r["rating"] is not None]
    if pc_strong or pc_weak:
        mb = statistics.mean(c0r) if c0r else float("nan")
        print("\n[H0a positive control] does the rating head move with argument QUALITY?")
        print(f"  STRONG arg : n={len(pc_strong)} ratings={sorted(pc_strong)}"
              + (f" mean={statistics.mean(pc_strong):.3f}" if pc_strong else ""))
        print(f"  baseline   : moderate c0 mean={mb:.3f}")
        print(f"  WEAK arg   : n={len(pc_weak)} ratings={sorted(pc_weak)}"
              + (f" mean={statistics.mean(pc_weak):.3f}" if pc_weak else ""))
        if pc_strong and pc_weak:
            delta = statistics.mean(pc_strong) - statistics.mean(pc_weak)
            verdict = ("PASS — head moves (>=0.15); the 0.72 source-null is interpretable"
                       if delta >= 0.15 else
                       "FAIL — head pinned even for quality; 0.72 is instrument-anchored on this item")
            print(f"  strong - weak = {delta:+.3f}  ->  {verdict}")

    if invalid:
        print("\n[invalid evals] (excluded — target never rated / degenerate):")
        for r in invalid:
            print(f"  {r['file']}  status={r['status']} rating={r['rating']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
