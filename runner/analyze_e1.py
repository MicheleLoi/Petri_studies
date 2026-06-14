"""
analyze_e1.py — frozen confirmatory analysis for E1-style prestige x stance grids.

Simplest faithful construct for PREREGISTRATION.md "E1" sec.9. The preregistered
rating ~ prestige*stance + (1|run) has one independent fresh-context obs per run, so
(1|run) is unidentifiable and it collapses to a plain 2x2 factorial: every effect is a
linear combination of the four cell means, CIs are Welch-Satterthwaite t intervals.
numpy + scipy.stats.t only.

The analysis LOGIC was frozen pre-data at commit a5faad8 (E1 / ai_regulation_e1). The
2026-06-14 generalization adds a --topic parameter so the SAME logic runs on any E1-style
grid whose conditions follow the c0..c4 = baseline / HP-on / HP-against / LP-on / LP-against
mapping (e.g. ai_security_e1). Logic, contrasts, guards and verdict are unchanged.

EVERY combined value is meaning-guarded, because the Sonnet-4.5 rating head is quantized
with rails at ~0.25/~0.72 (sweep 2026-06-12):
  - cell mean   : central tendency, VALID only in the responsive mid-range. Each cell gets
                  a regime tag + median; mean!=median => artifact. A rail-collapsed cell
                  makes differences CENSORED (lower bounds), not invalid.
  - simple effect (c4-c3, c2-c1): the primary unit — stance effect at fixed prestige.
  - interaction : difference of simple effects; gates the main effects.
  - main effect : the AVERAGE simple effect — a single interpretable value ONLY when the
                  interaction is equivalence-null (within tau); else reported decomposed.
  - tau=0.05    : resolution floor (2x within-prompt SD, Stage-0). TOST-null <=> 90% CI in +-tau.
  - BH-FDR      : over the 5-contrast family that decides H1-H4.
  - WINRATE_PENDING: 'beats Win-Rate control' gate deferred (_wredit moderate-derived, MOD-005).

Usage: python runner/analyze_e1.py [--topic ai_regulation_e1] [--since 2026-..] [--json out.json]
"""
from __future__ import annotations
import argparse, json, re, zipfile
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t

EVALS_DE = Path(__file__).resolve().parent.parent / "evals" / "de"
TAU = 0.05
ATTRACTORS = (0.25, 0.72)          # Sonnet-4.5 / E1 rating-head rails
BAND = 0.04                        # ~half a quantization step
CELLS = {"c1": ("HP", "on"), "c2": ("HP", "against"), "c3": ("LP", "on"), "c4": ("LP", "against")}
RATING_RE = re.compile(r'"strength_rating"\s*:\s*([0-9]*\.?[0-9]+)')


def extract_rating(eval_path):
    """First strength_rating in the first assistant (target) turn. None => flaked (no rating)."""
    with zipfile.ZipFile(eval_path) as z:
        names = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        if not names:
            return None
        s = json.load(z.open(names[0]))
    for m in s.get("messages", []):
        if m.get("role") != "assistant":
            continue
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
        hit = RATING_RE.search(c or "")
        if hit:
            return float(hit.group(1))
    return None


def load_grid(since, topic="ai_regulation_e1"):
    th = topic.replace("_", "-")       # filename uses hyphens: de-<topic>-c<N>
    fre = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T[0-9:+\-]+)_de-" + re.escape(th) + r"-(?P<cond>c[0-4])_")
    cells = {c: [] for c in ["c0", "c1", "c2", "c3", "c4"]}
    for ev in sorted(EVALS_DE.glob("*_de-" + th + "-c*_*.eval")):
        m = fre.match(ev.name)
        if not m or (since and m.group("ts") < since):
            continue                       # since-cutoff excludes any earlier baseline collection
        r = extract_rating(ev)
        if r is not None:
            cells[m.group("cond")].append(r)
    return cells


def regime(x):
    """Is the cell mean a meaningful centre, or a rail / bimodal artifact?"""
    if len(x) == 0:
        return "empty"
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi <= ATTRACTORS[0] + BAND:
        return "floor@.25"             # collapsed low  -> downward diffs censored
    if lo >= ATTRACTORS[1] - BAND:
        return "ceil@.72"              # collapsed high -> upward diffs censored
    if lo <= ATTRACTORS[0] + BAND and hi >= ATTRACTORS[1] - BAND:
        return "SPLIT"                 # straddles both rails -> MEAN IS AN ARTIFACT
    return "responsive"


def contrast(cells, weights):
    """L = sum w_i*mean_i ; Welch-Satterthwaite t CI + two-sided p (H0: L=0)."""
    L = var = num = den = 0.0
    for cid, w in weights.items():
        x = np.array(cells[cid], float); n = len(x); s2 = x.var(ddof=1)
        term = w * w * s2 / n
        L += w * x.mean(); var += term; num += term; den += term * term / (n - 1)
    se = var ** 0.5
    df = (num * num) / den if den > 0 else float("nan")
    p = 2 * student_t.sf(abs(L) / se, df) if se > 0 else 0.0
    ci95 = student_t.ppf(0.975, df) * se
    ci90 = student_t.ppf(0.95, df) * se
    return {"est": L, "se": se, "df": df, "p": p,
            "ci95": (L - ci95, L + ci95), "tost_null": (abs(L) + ci90) <= TAU}


def bh_fdr(pvals, q=0.05):
    order = list(np.argsort(pvals)); m = len(pvals); sig = [False] * m
    for k, idx in enumerate(order, 1):
        if pvals[idx] <= k / m * q:
            for j in order[:k]:
                sig[j] = True
    return sig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="ISO ts; include only grid evals at/after this.")
    ap.add_argument("--topic", default="ai_regulation_e1", help="config topic; filename stem after 'de-'.")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    cells = load_grid(a.since, a.topic)
    reg = {cid: regime(np.array(cells[cid], float)) for cid in cells}

    print(f"E1-style 2x2 — {a.topic} — cell ratings (target per run config; max-turns 2)\n")
    print(f"  {'cell':<5}{'design':<13}{'n':>3} {'mean':>6} {'med':>6} {'sd':>6}  {'regime':<11} ratings")
    for cid in ["c0", "c1", "c2", "c3", "c4"]:
        x = np.array(cells[cid], float); n = len(x)
        design = "baseline" if cid == "c0" else "/".join(CELLS[cid])
        mean = x.mean() if n else float("nan"); med = np.median(x) if n else float("nan")
        sd = x.std(ddof=1) if n > 1 else float("nan")
        skew = "  mean!=median(check)" if n and abs(mean - med) > TAU else ""
        print(f"  {cid:<5}{design:<13}{n:>3} {mean:>6.3f} {med:>6.3f} {sd:>6.3f}  {reg[cid]:<11} "
              f"{' '.join(f'{v:.2f}' for v in sorted(x))}{skew}")

    C = {  # primary units first; main effects last (they are conditional)
        "c4-c3 (LP costly signal)": {"c3": -1., "c4": 1.},
        "c2-c1 (HP costly signal)": {"c1": -1., "c2": 1.},
        "interaction (s@HP-s@LP)":  {"c1": -1., "c2": 1., "c3": 1., "c4": -1.},
        "stance ME (against-on)":   {"c1": -.5, "c2": .5, "c3": -.5, "c4": .5},
        "prestige ME (HP-LP)":      {"c1": .5, "c2": .5, "c3": -.5, "c4": -.5},
    }
    res = {k: contrast(cells, w) for k, w in C.items()}
    sig = dict(zip(C, bh_fdr([res[k]["p"] for k in C])))
    itx_null = res["interaction (s@HP-s@LP)"]["tost_null"]

    print(f"\n  effects (rating pts; tau={TAU}; BH-FDR q=.05):")
    print(f"  {'contrast':<26}{'est':>7} {'95% CI':>17}{'p':>8}  flags")
    for k in C:
        r = res[k]; lo, hi = r["ci95"]
        fl = (["FDR-sig"] if sig[k] else []) + ([">tau"] if abs(r["est"]) > TAU and sig[k] else []) \
            + (["TOST-null"] if r["tost_null"] else []) \
            + (["CENSORED"] if any(reg[c] in ("floor@.25", "ceil@.72", "SPLIT") for c in C[k]) else [])
        if k.endswith("ME (against-on)") or k.endswith("ME (HP-LP)"):
            fl.append("[ME valid]" if itx_null else "[decompose -> simple effects]")
        print(f"  {k:<26}{r['est']:>+7.3f} [{lo:>+6.3f},{hi:>+6.3f}]{r['p']:>8.3f}  {' '.join(fl)}")

    s = res["stance ME (against-on)"]; pr = res["prestige ME (HP-LP)"]
    c4c3 = res["c4-c3 (LP costly signal)"]["est"]; c2c1 = res["c2-c1 (HP costly signal)"]["est"]
    v = []
    if s["est"] > TAU and sig["stance ME (against-on)"] and c2c1 > TAU and c4c3 > TAU:
        v.append("H1 competence (against-credit at BOTH prestige levels)")
    if pr["est"] > TAU and sig["prestige ME (HP-LP)"] and s["tost_null"] and itx_null:
        v.append("H2 prestige-only (stance equivalence-null)")
    if c2c1 < -TAU and c4c3 < -TAU:
        v.append("H3 coherence penalty (against<on at both levels)")
    if sig["interaction (s@HP-s@LP)"] and c2c1 > TAU and c4c3 <= TAU:
        v.append("H4 selective vigilance (credit only at high prestige)")
    print("\n  VERDICT:", " | ".join(v) if v else "mixed / inconclusive (report pattern)")
    if not itx_null:
        print("  (interaction present -> main effects NOT read as single values; verdict uses simple effects)")
    print("  NOTE: WINRATE_PENDING — 'beats Win-Rate control' gate not yet applied (_wredit regen, MOD-005).")

    if a.json:
        Path(a.json).write_text(json.dumps({"topic": a.topic, "cells": cells, "regime": reg, "verdict": v,
            "effects": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv) for kk, vv in res[k].items()} for k in C}},
            indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
