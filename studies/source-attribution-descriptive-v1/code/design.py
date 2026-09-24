"""Offline materials, provider payloads and blocked schedules. No network functions."""
import json
import math
import random
import re
from pathlib import Path
from trace import ROOT, canonical, sha, write_new

SOURCE = ROOT.parent / "truth-management/review-20260922/stimuli_draft.json"
CELLS = ("CR_A", "CP_A", "AEI_A", "CE_A", "CR_B", "CP_B", "AEI_B", "CE_B")
WEIGHTS = (-.5, .5, -.5, .5, .5, -.5, .5, -.5)
MODELS = {
    "sonnet45": {"provider": "anthropic", "id": "claude-sonnet-4-5-20250929", "role": "candidate_primary"},
    "gpt4o": {"provider": "openai", "id": "gpt-4o-2024-08-06", "role": "candidate_replication"},
    "flash": {"provider": "vertex", "id": "gemini-3.5-flash", "role": "candidate_replication"},
    "lite": {"provider": "vertex", "id": "gemini-3.5-flash-lite", "role": "optional_candidate"},
}
RATING_KEYS = {"strength_rating", "strongest_point", "weakest_point", "overall_assessment"}
SMOKE_SYSTEM = "Return only the JSON requested by the user."
SMOKE_USER = 'Return exactly this JSON object: {"strength_rating":0.5,"strongest_point":"technical test","weakest_point":"technical test","overall_assessment":"technical test"}'


def payload(model, system, user, *, smoke=False):
    """Provider-specific encoding with the same substantive strings, prompt-only JSON."""
    info = MODELS[model]
    limit = 256 if smoke else 1024
    temp = 0 if smoke else 1
    if info["provider"] == "anthropic":
        return {"model": info["id"], "system": system, "messages": [{"role": "user", "content": user}],
                "max_tokens": limit, "temperature": temp, "thinking": {"type": "disabled"}}
    if info["provider"] == "openai":
        return {"model": info["id"], "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_completion_tokens": limit, "temperature": temp, "n": 1, "store": False}
    return {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": limit, "temperature": temp, "candidateCount": 1,
                                 "thinkingConfig": {"thinkingLevel": "MINIMAL"}}}


def request_spec(model, *, smoke=True, system=None, user=None):
    info = MODELS[model]
    urls = {"openai": "https://api.openai.com/v1/chat/completions", "anthropic": "https://api.anthropic.com/v1/messages",
            "vertex": f"https://aiplatform.eu.rep.googleapis.com/v1/projects/app-tracciabile-dev/locations/eu/publishers/google/models/{info['id']}:generateContent"}
    return {"model_key": model, "requested_model": info["id"], "provider": info["provider"], "endpoint": urls[info["provider"]],
            "payload": payload(model, SMOKE_SYSTEM if smoke else system, SMOKE_USER if smoke else user, smoke=smoke)}


def duplicate_guard(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("Duplicate JSON key")
        result[k] = v
    return result


def parse_rating(text):
    text = text.strip()
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.S)
        if not match:
            raise ValueError("Malformed/multiple code fences")
        text = match.group(1)
    def reject_constant(value):
        raise ValueError("Non-finite JSON constant")
    data = json.loads(text, object_pairs_hook=duplicate_guard, parse_constant=reject_constant)
    if not isinstance(data, dict) or set(data) != RATING_KEYS:
        raise ValueError("Expected exactly the four rating keys")
    score = data["strength_rating"]
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Rating must be a finite number in [0,1]")
    if any(not isinstance(data[k], str) or not data[k].strip() for k in RATING_KEYS - {"strength_rating"}):
        raise ValueError("Explanations must be nonempty strings")
    return data


def schedule(blocks, seed, models):
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks < 1:
        raise ValueError("Positive integer block count required")
    if len(set(models)) != len(models) or any(m not in MODELS for m in models):
        raise ValueError("Unknown or duplicate model")
    rng = random.Random(seed)
    result = []
    for block in range(1, blocks+1):
        # Every temporal block contains every condition of every included model once.
        slots = [(m, c) for m in models for c in CELLS]
        rng.shuffle(slots)
        for model, cell in slots:
            result.append(dict(slot=len(result)+1, block=block, model=model, cell=cell))
    return result


def build_manifest(materials, blocks=2, seed=20260922):
    cells = []
    for cell in CELLS:
        source, stimulus = cell.split("_")
        user = materials["user_template"].format(organization=materials["organizations"][source], argument=materials["arguments"][stimulus]["text"])
        messages = [{"role": "system", "content": materials["system"]}, {"role": "user", "content": user}]
        encodings = {model: request_spec(model, smoke=False, system=materials["system"], user=user) for model in MODELS}
        cells.append(dict(cell=cell, messages=messages, messages_sha256=sha(messages),
                          requests={m: {"spec": spec, "sha256": sha(spec)} for m, spec in encodings.items()}))
    return dict(phase="offline_only", status="not_frozen_not_registered_not_authorized_for_collection", cells=cells,
                model_candidates=MODELS, example_blocks=blocks, example_seed=seed,
                example_schedule=schedule(blocks, seed, list(MODELS)),
                serialization="UTF-8 sorted-key compact JSON, no NaN; hashes differ from old serializer by design",
                warning="Example blocks are not a sample-size decision. Model choices and decoding are working candidates.")


if __name__ == "__main__":
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifest = build_manifest(source)
    write_new(ROOT / "offline_manifest_v1.json", manifest)
    print(f"Built {len(manifest['cells'])} canonical cells, 32 payloads, 64 example slots; no API calls")
