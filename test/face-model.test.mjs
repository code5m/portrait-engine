import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { deriveFaceGeometry, deriveFaceStructureStyle, toPortraitCoordinates } from '../src/face-model.mjs';
import { defaults, decode, encode } from '../src/parameters.mjs';

const model = change => deriveFaceGeometry({ ...defaults(), ...change });
const read = file => fs.readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');

test('R007 uses one explicit face-local 207x304 frame, with finite anchors', () => {
  for (const faceWidth of [80, 100, 120]) {
    for (const jaw of [82, 100, 118]) {
      for (const eyeSpacing of [-16, 0, 16]) {
        const face = model({ faceWidth, jaw, eyeSpacing });
        assert.deepEqual(face.frame, { x: 87, y: 91, width: 207, height: 304, centerX: 103.5 });
        assert.equal(Object.keys(face.anchors).length, 16);
        for (const anchor of Object.values(face.anchors)) {
          assert.ok(anchor.x > 0 && anchor.x < face.frame.width, JSON.stringify(anchor));
          assert.ok(anchor.y > 0 && anchor.y < face.frame.height, JSON.stringify(anchor));
          const mapped = toPortraitCoordinates(face, anchor);
          assert.ok(mapped.x > 70 && mapped.x < 314, JSON.stringify(mapped));
          assert.ok(mapped.y > 91 && mapped.y < 395, JSON.stringify(mapped));
        }
        const a = face.anchors;
        assert.ok(a.leftEye.x < a.noseRoot.x && a.noseRoot.x < a.rightEye.x);
        assert.ok(a.leftJaw.x < a.noseBase.x && a.noseBase.x < a.rightJaw.x);
        assert.ok(a.leftAla.x < a.noseBase.x && a.noseBase.x < a.rightAla.x);
        assert.ok(a.leftCheek.x < a.noseRoot.x && a.noseRoot.x < a.rightCheek.x);
      }
    }
  }
});

test('R007 eye and eye socket share position; changing eye spacing moves both', () => {
  const narrow = model({ eyeSpacing: -16 }).anchors;
  const wide = model({ eyeSpacing: 16 }).anchors;
  assert.equal(narrow.leftEye.x, narrow.leftOrbit.x);
  assert.equal(wide.leftEye.x, wide.leftOrbit.x);
  assert.equal(narrow.rightEye.x, narrow.rightOrbit.x);
  assert.equal(wide.rightEye.x, wide.rightOrbit.x);
  assert.equal(wide.leftEye.x - narrow.leftEye.x, -32);
  assert.equal(wide.rightEye.x - narrow.rightEye.x, 32);
  assert.equal(wide.noseRoot.x, narrow.noseRoot.x, 'midline should not drift with eye spacing');
  assert.ok(wide.leftCheek.x < narrow.leftCheek.x, 'cheek follows eye socket');
});

test('R007 jaw controls jaw, chin and cheek together, without altering eye width', () => {
  const slim = model({ jaw: 82 }).anchors;
  const wide = model({ jaw: 118 }).anchors;
  assert.ok(wide.leftJaw.x < slim.leftJaw.x);
  assert.ok(wide.rightJaw.x > slim.rightJaw.x);
  assert.ok(wide.leftCheek.x < slim.leftCheek.x);
  assert.ok(wide.rightCheek.x > slim.rightCheek.x);
  assert.notEqual(wide.chin.y, slim.chin.y);
  assert.equal(wide.leftEye.x, slim.leftEye.x);
});

test('R007 nasal wing width is anchored to nose base, not independent absolute left/right', () => {
  const narrow = model({ noseWidth: 80 }).anchors;
  const wide = model({ noseWidth: 125 }).anchors;
  assert.ok(narrow.leftAla.x > wide.leftAla.x);
  assert.ok(narrow.rightAla.x < wide.rightAla.x);
  assert.equal((wide.leftAla.x + wide.rightAla.x)/2, wide.noseBase.x);
  assert.equal((narrow.leftAla.x + narrow.rightAla.x)/2, narrow.noseBase.x);
});

test('R007 face world coordinates honor external face scaling without double scaling', () => {
  const local = model({ faceWidth: 100 });
  const slim = model({ faceWidth: 80 });
  const wide = model({ faceWidth: 120 });
  const center = toPortraitCoordinates(wide, wide.anchors.noseRoot);
  assert.equal(center.x, toPortraitCoordinates(slim, slim.anchors.noseRoot).x);
  const leftSlim = toPortraitCoordinates(slim, slim.anchors.leftEye);
  const leftBase = toPortraitCoordinates(local, local.anchors.leftEye);
  const leftWide = toPortraitCoordinates(wide, wide.anchors.leftEye);
  assert.ok(leftSlim.x > leftBase.x && leftBase.x > leftWide.x);
});

test('R007 CSS protocol is derived from the very same 16 anatomical anchors', () => {
  const face = model({ eyeSpacing: 11, jaw: 118 });
  const vars = deriveFaceStructureStyle({ eyeSpacing: 11, jaw: 118 });
  assert.equal(Object.keys(vars).length, Object.keys(face.anchors).length * 2);
  for (const [key, val] of Object.entries(face.anchors)) {
    assert.equal(vars[`--fg-${key}-x`], `${val.x.toFixed(2)}px`);
    assert.equal(vars[`--fg-${key}-y`], `${val.y.toFixed(2)}px`);
  }
  assert.ok(Object.values(vars).every(v => /^(?:\d+|-?\d+\.\d{2})px$/.test(v)));
});

test('R007 CSS actually consumes shared orbit/nose/cheek/jaw variables, not fixed props', () => {
  const css = read('styles/study007.css');
  const index = read('index.html');
  const standalone = read('standalone.html');
  for (const name of ['leftEye','rightEye','leftOrbit','rightOrbit','noseRoot','leftAla','rightAla','leftCheek','rightCheek','leftJaw','rightJaw','chin']) {
    assert.match(css, new RegExp(`--fg-${name}-[xy]`), `unused anchor: ${name}`);
  }
  assert.match(css, /data-r007="structured"/);
  assert.doesNotMatch(css, /url\s*\(|<svg|<canvas|<img|data:image/i);
  assert.match(index, /href="\.\/styles\/study007\.css"/);
  assert.match(index, /src="\.\/src\/app\.mjs"/);
  assert.match(standalone, /Research 007: shared FaceGeometry anchors/);
  assert.doesNotMatch(standalone, /href="\.\/study\/007-compare\.html"/);
});

test('R007 experimental mode never mutates old seven/nine-parameter saved format', () => {
  const before = defaults();
  assert.equal(Object.keys(before).length, 9);
  for (const params of [{ faceWidth: 95, eyeSpacing: 8, jaw: 108 }, before]) {
    const encoded = encode(params);
    assert.doesNotMatch(encoded, /research|faceModel|r007/i);
    const readBack = decode(encoded);
    deriveFaceStructureStyle(readBack);
    assert.deepEqual(decode(encode(readBack)), readBack);
  }
  const page = read('src/app.mjs');
  assert.match(page, /if \(!researchEmbed && !volumeStudy\) restore\(\)/);
  assert.match(page, /if \(volumeStudy\) return/);
  assert.match(page, /root\.dataset\.r007 = faceVariant/);
});

test('R007 A/B comparison page must not present automated evaluation as human judgement', () => {
  const page = read('study/007-compare.html');
  assert.match(page, /r007=baseline&amp;embed=1/);
  assert.match(page, /r007=structured&amp;embed=1/);
  assert.match(page, /ART_UNVERIFIED/);
  assert.doesNotMatch(page, /<img\b|<svg\b|<canvas\b|https?:\/\//i);
});

test('R007 limited single-blind art rating protocol exports local JSON only', () => {
  const page = read('study/007-blind.html');
  assert.match(page, /portrait-engine-r007-blind/);
  assert.match(page, /r007=/);
  assert.match(page, /crypto\.getRandomValues/);
  assert.match(page, /ART_UNVERIFIED/);
  assert.match(page, /No automatic data transmission/);
  assert.doesNotMatch(page, /fetch\s*\(|XMLHttpRequest|navigator\.sendBeacon|<img|<svg|<canvas/i);
});
