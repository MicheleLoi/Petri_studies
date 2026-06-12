"""Throwaway: is the 0.72-everywhere a temperature=0 determinism artifact, or a
real attractor? Checks target temperature, prompt-identicalness across c0 runs,
meta-awareness language, and probe self-reports. Safe to delete."""
import zipfile, json, hashlib, csv, re
from pathlib import Path

EV = Path(r"C:\Users\loimi\Petri_studies\evals\de")
META = re.compile(r"\b(being (tested|evaluated)|this is a test|an evaluation|the auditor|red[- ]?team|you are testing|meta)\b", re.I)


def load(ev):
    with zipfile.ZipFile(ev) as z:
        sn = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        return json.load(z.open(sn[0]))


def msg_text(m):
    c = m.get("content", "")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    return c or ""


# 1. Target temperature — dump the resolved config of one target event, full.
sample0 = load(sorted(EV.glob("*-c0_*.eval"))[0])
tev = [e for e in sample0.get("events", []) if e.get("event") == "model" and e.get("role") == "target"]
print("=== one target ModelEvent: config + call.request (temperature hunt) ===")
if tev:
    e = tev[0]
    print("event['config'] =", json.dumps(e.get("config", {}), default=str)[:400])
    call = e.get("call") or {}
    req = call.get("request") if isinstance(call, dict) else None
    if isinstance(req, dict):
        print("call.request temperature =", req.get("temperature"),
              "| top_p =", req.get("top_p"), "| keys =", list(req.keys())[:15])
    else:
        print("call.request = (none/other);  call keys =", list(call.keys()) if isinstance(call, dict) else type(call))

# 2. Prompt identicalness + per-eval target temp across ALL c0 evals
print("\n=== c0 evals: target-input prompt hash + temperature ===")
hashes = {}
for ev in sorted(EV.glob("*-c0_*.eval")):
    s = load(ev)
    users = [m for m in s.get("messages", []) if m.get("role") == "user"]
    first = msg_text(users[0]) if users else ""
    h = hashlib.sha256(first.encode("utf-8")).hexdigest()[:10]
    hashes.setdefault(h, []).append(ev.name)
    tev = [e for e in s.get("events", []) if e.get("event") == "model" and e.get("role") == "target"]
    temp = None
    if tev:
        call = tev[0].get("call") or {}
        req = call.get("request") if isinstance(call, dict) else None
        temp = (req or {}).get("temperature") if isinstance(req, dict) else None
        if temp is None:
            temp = (tev[0].get("config") or {}).get("temperature")
    print(f"  {ev.name[:46]:48} temp={temp} prompt_hash={h} len={len(first)}")
print(f"  -> {len(hashes)} DISTINCT target-input prompt(s) across {sum(len(v) for v in hashes.values())} c0 evals")

# 3. Meta-awareness language in target outputs (all evals)
print("\n=== meta-awareness scan (target assistant messages) ===")
hits = 0; total = 0
for ev in sorted(EV.glob("*-ai-regulation-e1*.eval")):
    s = load(ev)
    for m in s.get("messages", []):
        if m.get("role") != "assistant":
            continue
        total += 1
        if META.search(msg_text(m)):
            hits += 1
print(f"  {hits}/{total} target messages contain eval-recognition language")

# 4. Probe self-reports vs measured (confabulation)
print("\n=== probe self-reports (confabulation check) ===")
csvp = EV / "_calibration_ledger.csv"
if csvp.exists():
    with open(csvp, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["eval_type"] == "probe":
                print(f"  {r['cell']:7} rating={r['rating']} | self-report dir={r['probe_dir']} "
                      f"mag={r['probe_mag']} predicted_no_source={r['probe_pred_no_source']}")
