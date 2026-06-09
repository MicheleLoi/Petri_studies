"""One-shot: extract target strength_ratings from the 7 Arm B .eval files.

Quick analysis tool — NOT a permanent runner component. Used 2026-06-05 to
compute Delta(Arm B - Arm A) for the UK carbon_tax 2-arm design.
"""
import zipfile, json, re, statistics
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals" / "uk"
arm_b = sorted(EVALS.glob("2026-06-05*_uk-carbon-tax-*.eval"))

results = []
for ev in arm_b:
    m = re.search(r"uk-carbon-tax-([a-z-]+)_[A-Za-z0-9]+\.eval$", ev.name)
    condition = m.group(1) if m else "?"
    with zipfile.ZipFile(ev) as z:
        with z.open("samples/1_epoch_1.json") as f:
            s = json.load(f)
    # Canonical rating = FIRST assistant response. Some conditions have
    # multi-turn auditor follow-up (notably progressive-tt where auditor
    # probed the model's self-report on attribution effect) and later
    # assistant turns don't carry the rating JSON.
    target_msg = None
    n_target_turns = 0
    for msg in s.get("messages", []):
        if msg.get("role") == "assistant":
            n_target_turns += 1
            if target_msg is None:
                target_msg = msg
    content = target_msg.get("content", "") if target_msg else ""
    if isinstance(content, list):
        content = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
    jm = re.search(r'\{[^{}]*"strength_rating"[^{}]*\}', content, re.DOTALL)
    rating = None
    strongest = ""
    weakest = ""
    overall = ""
    if jm:
        try:
            j = json.loads(jm.group(0))
            rating = j.get("strength_rating")
            strongest = (j.get("strongest_point") or "")[:120]
            weakest = (j.get("weakest_point") or "")[:120]
            overall = (j.get("overall_assessment") or "")[:120]
        except Exception:
            pass
    results.append({
        "condition": condition, "rating": rating,
        "strongest": strongest, "weakest": weakest, "overall": overall,
        "file": ev.name, "n_target_turns": n_target_turns,
    })

# Order results in the expected canonical order
canonical = ["baseline", "generic", "green-actor", "progressive-tt", "right-actor", "conservative-tt", "neutral-institution"]
results_ordered = []
for c in canonical:
    for r in results:
        if r["condition"] == c:
            results_ordered.append(r)
            break

ratings = [r["rating"] for r in results_ordered if r["rating"] is not None]

print("=" * 90)
print(f'{"Condition":<22} {"Rating":<8} {"Turns":<6} {"Strongest point (first 50 ch)":<55}')
print("-" * 90)
for r in results_ordered:
    rs = f'{r["rating"]:.3f}' if r["rating"] is not None else "???"
    nt = str(r["n_target_turns"])
    print(f'{r["condition"]:<22} {rs:<8} {nt:<6} {r["strongest"][:55]:<55}')
print("-" * 90)
print()
print("Aggregate Arm B (Sonnet 4.6, fresh context per condition):")
print(f"  mean   = {statistics.mean(ratings):.4f}")
print(f"  stdev  = {statistics.stdev(ratings):.4f}")
print(f"  min    = {min(ratings):.3f}")
print(f"  max    = {max(ratings):.3f}")
print(f"  range  = {max(ratings) - min(ratings):.3f}")
print()
print("Comparison with Arm A (Sonnet 4.6, continuous context, T1' FIX A):")
print("  Arm A ratings: 0.680 x 7 (character-by-character identical)")
print("  Arm A stdev:   0.0000")
print()
print(f"DELTA: Arm B variance ({max(ratings) - min(ratings):.3f}) - Arm A variance (0.000) = {max(ratings) - min(ratings):.3f}")
print()
print("Asymmetry pattern (left vs right vs neutral vs control):")
left = [r["rating"] for r in results_ordered if r["condition"] in ("green-actor", "progressive-tt") and r["rating"] is not None]
right = [r["rating"] for r in results_ordered if r["condition"] in ("right-actor", "conservative-tt") and r["rating"] is not None]
neutral = [r["rating"] for r in results_ordered if r["condition"] == "neutral-institution" and r["rating"] is not None]
control = [r["rating"] for r in results_ordered if r["condition"] in ("baseline", "generic") and r["rating"] is not None]
if control:
    print(f"  control mean (baseline+generic)            : {statistics.mean(control):.3f}")
if left:
    print(f"  left mean (green-actor+progressive-tt)     : {statistics.mean(left):.3f}  | shift vs control: {statistics.mean(left)-statistics.mean(control):+.3f}")
if right:
    print(f"  right mean (right-actor+conservative-tt)   : {statistics.mean(right):.3f}  | shift vs control: {statistics.mean(right)-statistics.mean(control):+.3f}")
if neutral:
    print(f"  neutral (IFS)                              : {neutral[0]:.3f}  | shift vs control: {neutral[0]-statistics.mean(control):+.3f}")
print()
print("Per-condition descriptors (strongest/weakest/overall, first 90 ch each):")
for r in results_ordered:
    print(f"  [{r['condition']}]")
    print(f"    strongest: {r['strongest']}")
    print(f"    weakest:   {r['weakest']}")
    print(f"    overall:   {r['overall']}")
