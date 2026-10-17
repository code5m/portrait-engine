"""Validate cached S2 geometry exactly, except the non-rendering LAPACK residual.

Mesh bytes, weights, camera, renderer payload and source hashes remain exact.
The best affine-fit RMS is diagnostic (never consumed by the CSS painter), and
its final floating-point bits may differ between LAPACK/CPU implementations.
This validator neither rewrites descriptors nor accepts cached PASS reports.
"""
from __future__ import annotations
import json
import math

SIGNATURE_FIELDS = {'geometryHash', 'nonAffineRMS', 'weights', 'camera', 'surfaceOnly'}


def assert_signature(actual, expected, label='S2'):
    if not isinstance(actual, dict) or set(actual) != SIGNATURE_FIELDS or set(expected) != SIGNATURE_FIELDS:
        raise AssertionError(label + ': unexpected geometry signature schema')
    for key in sorted(SIGNATURE_FIELDS - {'nonAffineRMS'}):
        if actual[key] != expected[key]:
            raise AssertionError(f'{label}: exact geometry field {key} mismatch: {actual[key]!r} != {expected[key]!r}')
    a, b = actual['nonAffineRMS'], expected['nonAffineRMS']
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in (a, b)):
        raise AssertionError(label + ': invalid affine-fit diagnostic')
    if not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14):
        raise AssertionError(f'{label}: affine-fit diagnostic changed: {a!r} != {b!r}')
    return abs(a - b)


def main():
    import numpy as np
    from model import CONFIG, CACHE, HeadModel, source_digest, canonical, sha, unit
    model = HeadModel()
    expected = {i['id'] + '-' + l['id'] for i in CONFIG['identities'] for l in CONFIG['lights']}
    assert len(expected) == 18
    assert {p.stem for p in (CACHE / 'renders').glob('*.json')} == expected, 'S2 cache cohort mismatch'
    diagnostic_deltas = []
    for identity in CONFIG['identities']:
        geometry = model.signature(identity['weights'])
        for light in CONFIG['lights']:
            case = identity['id'] + '-' + light['id']
            d = json.loads((CACHE / 'renders' / (case + '.json')).read_text())
            assert d['stage'] == 'S2' and d['sourceDigest'] == source_digest(), case + ': stale source'
            assert d['fixtureId'] == case and d['split'] == identity['split'], case + ': wrong fixture'
            delta = assert_signature(d['geometry'], geometry, case)
            if delta:
                diagnostic_deltas.append({'case': case, 'nonRenderingRMSDelta': delta})
            assert np.allclose(d['light'], unit(light['direction']), rtol=0, atol=1e-14), case + ': wrong light'
            payload = {k: v for k, v in d.items() if k not in {'contentHash', 'timingSeconds', 'fixtureId', 'split'}}
            assert d['contentHash'] == sha(canonical(payload)), case + ': changed descriptor bytes'
    print('S2_CACHE_DIAGNOSTICS ' + json.dumps(diagnostic_deltas, separators=(',', ':')))
    print('S2_ALL_18_NUMERIC_DESCRIPTORS_VALIDATED; exact mesh and painter hashes; fresh reference, CSS and UI required')


if __name__ == '__main__':
    main()
