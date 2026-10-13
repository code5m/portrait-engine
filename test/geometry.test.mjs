import test from 'node:test';
import assert from 'node:assert/strict';
import { derivePortraitStyle } from '../src/geometry.mjs';
import { decode, encode, defaults } from '../src/parameters.mjs';

const at = (partial) => derivePortraitStyle({ ...defaults(), ...partial });
test('ear landmark and hair mass follow both face-width extremes', () => {
  const narrow = at({ faceWidth: 80 });
  const standard = at({ faceWidth: 100 });
  const wide = at({ faceWidth: 120 });
  assert.equal(standard['--face-half-delta'], '0.00px');
  assert.equal(narrow['--face-half-delta'], '-20.70px');
  assert.equal(wide['--face-half-delta'], '20.70px');
  assert.ok(+narrow['--hair-structure-x'] < +standard['--hair-structure-x']);
  assert.ok(+standard['--hair-structure-x'] < +wide['--hair-structure-x']);
  assert.equal(wide['--hair-x'],wide['--hair-structure-x']);
});
test('light direction moves highlights and switches the shadowed cheek', () => {
  const left = at({ lightDirection: -60 });
  const right = at({ lightDirection: 60 });
  assert.equal(left['--light-x'], '28.0%');
  assert.equal(right['--light-x'], '72.0%');
  assert.equal(left['--shadow-x'], '72.0%');
  assert.equal(right['--shadow-x'], '28.0%');
  assert.ok(+left['--shadow-right-opacity'] > +left['--shadow-left-opacity']);
  assert.ok(+right['--shadow-left-opacity'] > +right['--shadow-right-opacity']);
  assert.equal(left['--nose-cast-x'], '5.0px');
  assert.equal(right['--nose-cast-x'], '-5.0px');
});
test('mouth width is clamped and all derived CSS values stay finite', () => {
  for (const faceWidth of [80, 100, 120]) for (const lightDirection of [-60, -30, 60]) {
    const style = at({ faceWidth, lightDirection, mouthWidth: 200 });
    assert.equal(style['--mouth-x'], '1.18');
    assert.ok(Object.values(style).every(value => !/NaN|Infinity|undefined/.test(value)));
  }
});
test('previous 7-control v1 portraits still import with new controls set to defaults', () => {
  const oldFile = JSON.stringify({ format: 'portrait-engine-params', version: 1,
    parameters: { faceWidth: 90, eyeSpacing: 4, noseWidth: 88, jaw: 92,
      graphite: 50, hatching: 51, hairVolume: 105 }});
  const decoded = decode(oldFile);
  assert.equal(decoded.faceWidth, 90);
  assert.equal(decoded.lightDirection, defaults().lightDirection);
  assert.equal(decoded.mouthWidth, defaults().mouthWidth);
  assert.deepEqual(decode(encode(decoded)), decoded);
});
