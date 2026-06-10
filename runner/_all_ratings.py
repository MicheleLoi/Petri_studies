"""Throwaway: extract EVERY strength_rating from a transcript (all assistant turns).
Used to pull the 7 per-condition ratings from the Arm A continuous-context trials."""
import sys, zipfile, json, re
from pathlib import Path

for ev in sys.argv[1:]:
    p = Path(ev)
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        s = json.load(z.open(names[0]))
    ratings = []
    for m in s.get("messages", []):
        if m.get("role") == "assistant":
            c = m.get("content", "")
            if isinstance(c, list):
                c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
            for jm in re.finditer(r'"strength_rating"\s*:\s*([0-9.]+)', c or ""):
                ratings.append(float(jm.group(1)))
    n_asst = sum(1 for m in s.get("messages", []) if m.get("role") == "assistant")
    print(f"{p.name}")
    print(f"   assistant turns={n_asst}  ratings found={len(ratings)}  values={ratings}")
