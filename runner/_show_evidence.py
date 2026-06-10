"""Throwaway: dump verbatim target outputs + judge scores for given .eval files,
so a human can verify conclusions against raw evidence (not the analysis tool)."""
import sys, zipfile, json
from pathlib import Path

for ev in sys.argv[1:]:
    p = Path(ev)
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        s = json.load(z.open(names[0]))
    print("=" * 100)
    print("FILE:", p.name)
    msgs = s.get("messages", [])
    for i, m in enumerate(msgs):
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
        c = (c or "").strip()
        print(f"\n--- msg[{i}] {role.upper()} ---")
        print(c[:1400])
    # Judge scores (what the JUDGE produced — NOT used by analyze_stage0.py conclusions)
    sc = s.get("scores") or {}
    print("\n--- JUDGE SCORES (from .eval; NOT used in H0a/tau/confab conclusions) ---")
    print(json.dumps(sc, indent=2)[:1200])
