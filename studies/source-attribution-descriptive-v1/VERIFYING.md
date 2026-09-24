# Independent verification

`MANIFEST.json` maps each included relative filename to the lowercase hexadecimal SHA-256 of that file's **exact bytes**, with no text or line-ending normalization. The manifest itself is hashed separately. The published release should state its digest and commit. `.gitattributes` preserves package bytes when Git checks files in or out.

Run `python -B verify_manifest.py` from this directory. To compare with an independently recorded digest, use `python -B verify_manifest.py --expected-manifest-sha256 THE_PUBLISHED_DIGEST`. This uses only Python's standard library and does not contact Giano, GitHub or any model provider. It rejects missing, changed and extra files, except local Python caches and test temporary files.

`plan.json` additionally records payload hashes. Those hash UTF-8 JSON serialized using Python `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`. There is no trailing newline in the bytes used for these object hashes. `python -B code/main_runner.py verify --package .` verifies both manifest files and these payload specifications. Authentication headers are not part of the published payloads.

A matching hash establishes identity relative to the referenced manifest, not truth, authorship or a date by itself. The public GitHub publication record establishes the claimed public chronology; the private Giano trail links to the same hash but is not needed to inspect or verify the public scientific package. A replacement manifest must be treated as a new version, not silent continuation of this one.
