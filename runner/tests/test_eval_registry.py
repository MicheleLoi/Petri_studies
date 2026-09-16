from pathlib import Path
import sys

RUNNER = Path(__file__).resolve().parents[1]
if str(RUNNER) not in sys.path:
    sys.path.insert(0, str(RUNNER))

import eval_registry


def test_append_entries_preserves_existing_bytes(tmp_path, monkeypatch):
    journal = tmp_path / "lab_journal.md"
    prefix = b"historical\r\nbytes-without-final-newline"
    journal.write_bytes(prefix)
    monkeypatch.setattr(eval_registry, "LAB_JOURNAL", journal)

    eval_registry.append_entries(["\n## new entry\n"])

    result = journal.read_bytes()
    assert result.startswith(prefix)
    assert result == prefix + b"\n## new entry\n"


def test_unbound_eval_is_not_assigned_to_current_session():
    meta = {
        "created": "2026-01-01T00:00:00Z",
        "polity": "uk",
        "topic": "carbon_tax",
        "condition": "baseline",
        "rel_path": "uk/example.eval",
        "eval_id": "example",
        "task_name": "uk_carbon_tax_baseline",
        "status": "success",
        "auditor": "a",
        "target": "t",
        "judge": "j",
        "total_time": None,
        "token_usage": {},
        "scores": {},
    }

    entry = eval_registry.format_entry(meta)

    assert "[GIANO_SESSION_UNKNOWN]" in entry
    assert "MHC" not in entry
