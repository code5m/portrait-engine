import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { defaults, normalize } from '../src/parameters.mjs';
import { deriveHeadLandmarks, derivePortraitStyle } from '../src/geometry.mjs';

const sample = defaults();

test('canonical facial landmarks agree with CSS coordinate system', () => {
  const p = deriveHeadLandmarks(sample);
  assert.equal(p.faceWidth, 207);
  assert.equal(p.faceLeft, 87);
  assert.equal(p.faceRight, 294);
  assert.equal(p.centerX, 190.5);
  assert.equal(p.leftEar, 89);
  assert.equal(p.rightEar, 294);
  assert.equal(p.leftEye, 144.5);
  assert.equal(p.rightEye, 235.5);
  assert.equal(p.eyeY, 249.5);
  assert.ok(p.noseBaseY > p.eyeY && p.mouthY > p.noseBaseY && p.chinY > p.mouthY);
});

test('9 geometry x light scenarios remain finite and coordinated', () => {
  for (const faceWidth of [80, 100, 120]) {
    for (const lightDirection of [-60, 0, 60]) {
      const p = normalize({ ...sample, faceWidth, lightDirection });
      const lm = deriveHeadLandmarks(p);
      const s = derivePortraitStyle(p);
      assert.ok(lm.leftEar < lm.faceLeft + 30, `left ear disconnected ${faceWidth}`);
      assert.ok(lm.rightEar > lm.faceRight - 30, `right ear disconnected ${faceWidth}`);
      assert.ok(lm.leftEye < lm.rightEye);
      assert.ok(lm.leftEye > lm.faceLeft && lm.rightEye < lm.faceRight);
      for (const [name, value] of Object.entries(s)) {
        assert.doesNotMatch(String(value), /NaN|Infinity|undefined/, name);
      }
      assert.equal(s['--face-x'], String(faceWidth / 100));
      assert.equal(s['--key-light'], ((lightDirection + 60) / 120).toFixed(4));
    }
  }
});

test('shadow and light switches are mirror-consistent', () => {
  const left = derivePortraitStyle({ ...sample, lightDirection: -60 });
  const right = derivePortraitStyle({ ...sample, lightDirection: 60 });
  const middle = derivePortraitStyle({ ...sample, lightDirection: 0 });
  assert.equal(left['--plane-shade-right'], right['--plane-shade-left']);
  assert.equal(left['--plane-shade-left'], right['--plane-shade-right']);
  assert.equal(middle['--plane-shade-right'], middle['--plane-shade-left']);
  assert.ok(+left['--plane-shade-right'] > +left['--plane-shade-left']);
  assert.ok(+right['--plane-shade-right'] < +right['--plane-shade-left']);
});

test('anatomy and drawing stroke files have no raster or vector assets', () => {
  for (const path of ['anatomy.css','graphite.css']) {
    const css=fs.readFileSync(new URL('../styles/' + path, import.meta.url),'utf8');
    assert.doesNotMatch(css, /(?:url\s*\(|data:image|base64|<svg)/i);
    assert.match(css, /radial-gradient\(/);
  }
  const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
  for (const cls of ['eye-socket','brow-bone','cheek-plane','jaw-plane','nasal-plane','chin-plane','hair-sweep']) {
    assert.ok(new RegExp('class=\"' + cls + '(?:\\s|\")').test(html), `Missing anatomical layer ${cls}`);
  }
});
