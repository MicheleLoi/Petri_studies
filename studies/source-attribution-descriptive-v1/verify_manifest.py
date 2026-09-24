"""Verify exact published bytes using only the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--expected-manifest-sha256')
a = p.parse_args()
root = Path(__file__).resolve().parent
raw = (root / 'MANIFEST.json').read_bytes()
digest = hashlib.sha256(raw).hexdigest()
if a.expected_manifest_sha256 and digest != a.expected_manifest_sha256.lower():
    raise SystemExit('Manifest differs from the independently recorded digest')
manifest = json.loads(raw)
listed = set(manifest['files'])
for rel, expected in manifest['files'].items():
    target = (root / rel).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise SystemExit('Missing or invalid path: ' + rel)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise SystemExit('File hash mismatch: ' + rel)
actual = {f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()
          and not any(part in ('__pycache__', 'tmp-main-tests') for part in f.relative_to(root).parts)}
if actual != listed | {'MANIFEST.json'}:
    raise SystemExit('Unexpected package file set: ' + str(sorted(actual ^ (listed | {'MANIFEST.json'}))))
print(json.dumps({'verified': True, 'files': len(listed), 'manifest_sha256': digest, 'network_calls': 0}))
