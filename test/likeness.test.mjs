import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { defaults } from '../src/parameters.mjs';
import { deriveHeadLandmarks } from '../src/geometry.mjs';

const css=fs.readFileSync(new URL('../styles/likeness.css',import.meta.url),'utf8');
const html=fs.readFileSync(new URL('../index.html',import.meta.url),'utf8');
const build=fs.readFileSync(new URL('../scripts/build-standalone.py',import.meta.url),'utf8');
const qa=fs.readFileSync(new URL('../test/browser-qa.py',import.meta.url),'utf8');

test('the same original CSS art is wired into application, offline build and browser QA',()=>{
  assert.match(html,/href="\.\/styles\/likeness\.css"/);
  assert.match(build,/'likeness'/);
  assert.match(qa,/'likeness'/);
  assert.match(qa,/QA did not inline every CSS file/);
  assert.doesNotMatch(css,/(?:url\s*\(|data:image|base64|<svg|<canvas|<img)/i);
});

test('paired eyes use purposefully distinct upper-lid and iris decisions',()=>{
  assert.match(css,/\.portrait \.eye-left \{/);
  assert.match(css,/\.portrait \.eye-right \{/);
  assert.match(css,/\.portrait \.eye-right::after/);
  assert.match(css,/\.portrait \.eye-right \.iris/);
  assert.match(css,/\.portrait \.mouth::before/);
});

test('landmarks use the actual smaller, asymmetrical eye groups across width variants',()=>{
  const widths=[80,90,100,110,120];
  for(const faceWidth of widths){
    for(const eyeSpacing of [-16,0,16]){
      const face=deriveHeadLandmarks({...defaults(),faceWidth,eyeSpacing});
      const scale=faceWidth/100;
      assert.equal(face.leftEye,190.5-(46+eyeSpacing)*scale);
      assert.equal(face.rightEye,190.5+(45+eyeSpacing)*scale);
      assert.ok(face.leftEye > face.faceLeft);
      assert.ok(face.rightEye < face.faceRight);
      assert.ok(face.leftEye < face.rightEye);
      assert.ok(face.eyeY > face.browY);
      assert.ok(face.noseBaseY > face.eyeY && face.mouthY>face.noseBaseY);
    }
  }
});

test('offline build ships likeness code, no hidden fallback',()=>{
  const offline=fs.readFileSync(new URL('../standalone.html',import.meta.url),'utf8');
  assert.match(offline,/Research 003/);
  assert.doesNotMatch(offline,/<link\s+rel="stylesheet"/);
  assert.doesNotMatch(offline,/<(?:img|svg|canvas)\b/i);
  assert.doesNotMatch(offline,/<script\s+type="module"\s+src=/);
});
