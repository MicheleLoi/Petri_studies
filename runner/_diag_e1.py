"""Throwaway diagnostic: open a .eval and dump roles, per-model usage, messages,
and per-model-event usage field names. Used to design the calibration ledger
extractor. Safe to delete."""
import zipfile, json, pprint, sys

p = sys.argv[1]
z = zipfile.ZipFile(p)
h = json.load(z.open('header.json')); ev = h.get('eval', {})
print('STATUS:', h.get('status'))
print('MODEL_ROLES:', ev.get('model_roles'))

s = json.load(z.open('summaries.json'))[0]
print('\n=== MODEL_USAGE (summaries[0]) ===')
pprint.pprint(s.get('model_usage'))
print('\n=== SCORES ===')
pprint.pprint(s.get('scores'))
print('TOTAL_TIME:', s.get('total_time'))

names = z.namelist()
sn = [n for n in names if n.startswith('samples/') and n.endswith('.json')]
samp = json.load(z.open(sn[0]))
msgs = samp.get('messages', [])
print('\n=== %d MESSAGES ===' % len(msgs))
for i, m in enumerate(msgs):
    role = m.get('role'); c = m.get('content', '')
    if isinstance(c, list):
        c = ' '.join(x.get('text', '') if isinstance(x, dict) else str(x) for x in c)
    print('[%d] role=%r model=%r len=%d' % (i, role, m.get('model'), len(c or '')))
    print('     ', (c or '').replace(chr(10), ' ')[:240])

evs = samp.get('events', [])
mevs = [e for e in evs if e.get('event') == 'model']
print('\n=== %d model events ===' % len(mevs))
if mevs:
    e0 = mevs[0]
    print('event[0] keys:', list(e0.keys()))
    out = e0.get('output', {})
    print('output keys:', list(out.keys()) if isinstance(out, dict) else type(out))
    u0 = out.get('usage') if isinstance(out, dict) else None
    print('output.usage:', u0)
    for e in mevs:
        out = e.get('output', {}) or {}
        u = out.get('usage') or {}
        print('  model=%s role=%s in=%s out=%s usage_keys=%s'
              % (e.get('model'), e.get('role'), u.get('input_tokens'), u.get('output_tokens'), list(u.keys())))
