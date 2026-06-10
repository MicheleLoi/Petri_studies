"""Extract per-condition (source, rating) + model from the published DE/CH
'coherence-*' source-attribution study evals, for a reliability analysis.
Outputs JSON to stdout."""
import sys, zipfile, json, re
from pathlib import Path

ARCHIVE = Path(r"C:\Users\loimi\Petri_studies\_archive\logs")

def load_sample_and_model(p):
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if n.startswith("samples/") and n.endswith(".json")]
        s = json.load(z.open(names[0]))
        try:
            h = json.load(z.open("header.json"))
            roles = (h.get("eval", {}) or {}).get("model_roles", {}) or {}
            target = (roles.get("target", {}) or {}).get("model")
        except Exception:
            target = None
    models = list((s.get("model_usage") or {}).keys())
    return s, models, target

def preamble(text):
    # first line / up to the source attribution, before the argument quote
    t = (text or "").strip().replace("\n", " ")
    # cut at the first long quote (the argument)
    cut = t.find('"')
    head = t[:cut] if 0 < cut < 200 else t[:160]
    return head.strip()

recs = []
files = sorted(ARCHIVE.glob("*coherence-*.eval"))
for p in files:
    try:
        s, models, target = load_sample_and_model(p)
    except Exception as e:
        recs.append({"file": p.name, "error": str(e)})
        continue
    msgs = s.get("messages", [])
    pairs = []
    pending_user = None
    for m in msgs:
        role = m.get("role")
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
        if role == "user":
            pending_user = c
        elif role == "assistant":
            jm = re.search(r'"strength_rating"\s*:\s*([0-9.]+)', c or "")
            if jm:
                pairs.append({"source": preamble(pending_user) if pending_user else None,
                              "rating": float(jm.group(1))})
                pending_user = None
    ratings = [pr["rating"] for pr in pairs]
    polity = "CH" if "swiss" in p.name.lower() else "DE"
    mtopic = re.search(r"coherence-(?:swiss-)?(.+?)_[A-Za-z0-9]{16,}\.eval$", p.name)
    rec = {
        "file": p.name,
        "polity": polity,
        "topic": mtopic.group(1) if mtopic else "?",
        "target_model": target,
        "models": models,
        "n_conditions": len(ratings),
        "ratings": ratings,
        "baseline": ratings[0] if ratings else None,
        "min": min(ratings) if ratings else None,
        "max": max(ratings) if ratings else None,
        "range": round(max(ratings) - min(ratings), 3) if ratings else None,
        "pairs": pairs,
    }
    recs.append(rec)

print(json.dumps(recs, indent=1))
