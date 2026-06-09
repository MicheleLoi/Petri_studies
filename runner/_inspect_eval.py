"""Throwaway: inspect a .eval's internal structure to debug rating extraction."""
import sys, zipfile, json
from pathlib import Path

ev = Path(sys.argv[1])
with zipfile.ZipFile(ev) as z:
    names = z.namelist()
    print("=== namelist (first 40) ===")
    for n in names[:40]:
        print(" ", n)
    sample_names = [n for n in names if n.startswith("samples/") and n.endswith(".json")]
    print("\n=== sample json files ===", sample_names)
    if sample_names:
        with z.open(sample_names[0]) as f:
            s = json.load(f)
        msgs = s.get("messages", [])
        print(f"\n=== {len(msgs)} messages ===")
        for i, m in enumerate(msgs):
            role = m.get("role")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
            content = (content or "").replace("\n", " ")
            print(f"[{i}] role={role!r} len={len(content)}  {content[:200]}")
        print("\n=== top-level sample keys ===", list(s.keys()))
