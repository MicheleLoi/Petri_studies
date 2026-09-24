"""One append-only event source, two views: JSONL and human-readable Markdown."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def read_events(root=ROOT):
    path = Path(root) / "events.jsonl"
    events = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    previous = None
    for n, event in enumerate(events, 1):
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        if event["id"] != f"E{n:04}" or event["previous_sha256"] != previous or sha(body) != event["event_sha256"]:
            raise ValueError("Event log failed integrity check")
        previous = event["event_sha256"]
    return events


def render_diary(root=ROOT):
    root = Path(root)
    events = read_events(root)
    rows = ["# Diario di costruzione dello studio", "", "Vista generata da `events.jsonl`; gli ID collegano racconto e dati. Le valutazioni dell'assistente sono distinte dai mandati dell'autore. Questa traccia scientifica privata non sostituisce il registro di Giano.", ""]
    for e in events:
        rows += [f"## {e['id']} — {e['title']}", "", f"{e['timestamp_utc']} · {e['authority']} · fase: {e['phase']}", "", e["what"], "", "**Perché:** " + e["why"], "", "**Esito e conseguenze:** " + e["outcome"], ""]
        if e.get("artifacts"):
            rows += ["**Reperti:** " + "; ".join(f"[{a['path']}]({a['path']})" for a in e["artifacts"]), ""]
        if e.get("limits"):
            rows += ["**Limiti:** " + e["limits"], ""]
    (root / "DIARIO.md").write_text("\n".join(rows), encoding="utf-8")


def record(*, title, authority, phase, what, why, outcome, artifacts=(), limits="", details=None, root=ROOT):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Exclusive local lock: concurrent appenders fail instead of interleaving records.
    lock = root / ".trace.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        events = read_events(root)
        event = dict(id=f"E{len(events)+1:04}", timestamp_utc=now(), title=title,
                     authority=authority, phase=phase, what=what, why=why, outcome=outcome,
                     limits=limits, artifacts=[{"path": str(p).replace("\\", "/"), "sha256": file_sha(root/p)} for p in artifacts],
                     details=details or {}, previous_sha256=events[-1]["event_sha256"] if events else None)
        event["event_sha256"] = sha(event)
        with (root / "events.jsonl").open("a", encoding="utf-8", newline="\n") as f:
            f.write(canonical(event).decode("utf-8") + "\n")
            f.flush()
            os.fsync(f.fileno())
        render_diary(root)
        return event
    finally:
        os.close(fd)
        lock.unlink()


if __name__ == "__main__":
    render_diary()
    print(f"Verified {len(read_events())} events; rendered DIARIO.md")
