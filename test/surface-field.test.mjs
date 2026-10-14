import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { deriveRelief, deriveSurfaceField, deriveSurfaceFieldStyle } from '../src/surface-field.mjs';
import { defaults, encode, decode } from '../src/parameters.mjs';
const read = path => fs.readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('R008 relief uses the same 16 face anchors with smooth bounded normals', () => {
  for (const faceWidth of [80,100,120]) for (const jaw of [82,100,118]) {
    const f = deriveRelief({...defaults(), faceWidth,jaw});
    assert.equal(Object.keys(f.face.anchors).length, 16);
    for (const x of [19,63,103,151,189]) for (const y of [45,145,237,290]) {
      const h = f.heightAt(x,y);
      const n = f.normalAt(x,y);
      assert.ok(Number.isFinite(h) && Math.abs(h)<120);
      assert.ok(n.every(v=>Number.isFinite(v)));
      assert.ok(Math.abs(Math.hypot(...n)-1)<1e-10);
      assert.ok(n[2]>0);
      assert.ok(Math.abs(f.heightAt(x+.01,y)-h)<.5,'continuous depth, no patch seams');
    }
  }
});

test('R008 eye socket is recessed, nose base protrudes, both from the same face model', () => {
  const f=deriveRelief(defaults());const a=f.face.anchors;
  assert.ok(f.heightAt(a.leftOrbit.x,a.leftOrbit.y)<f.heightAt(a.leftBrow.x,a.leftBrow.y));
  assert.ok(f.heightAt(a.noseBase.x,a.noseBase.y)>f.heightAt(a.leftCheek.x,a.leftCheek.y));
  assert.ok(f.heightAt(a.noseBase.x,a.noseBase.y)>f.heightAt(a.mouth.x,a.mouth.y));
});

test('R008 one light vector gives directional opposite-side nose and cheek shadows', () => {
  const left=deriveSurfaceField({lightDirection:-60}),right=deriveSurfaceField({lightDirection:60});
  for(const key of ['nose','cheek','jaw']) {
    assert.ok(left.values[`${key}Left`].shade < left.values[`${key}Right`].shade, key);
    assert.ok(right.values[`${key}Left`].shade > right.values[`${key}Right`].shade, key);
  }
  assert.ok(left.noseCast.x>12);
  assert.ok(right.noseCast.x< -12);
  assert.ok(left.noseCast.opacity>0 && left.noseCast.opacity<.35);
  assert.equal(left.noseCast.centerX,right.noseCast.centerX);
});

test('R008 changing jaw geometry also changes form normals and stroke angles', () => {
  const slim=deriveSurfaceField({jaw:82,lightDirection:-60});
  const wide=deriveSurfaceField({jaw:118,lightDirection:-60});
  assert.notEqual(slim.cheekAngles.left,wide.cheekAngles.left);
  assert.notEqual(slim.cheekAngles.right,wide.cheekAngles.right);
  assert.notEqual(slim.values.cheekLeft.shade,wide.values.cheekLeft.shade);
  assert.ok(Math.abs(slim.face.anchors.leftJaw.x-wide.face.anchors.leftJaw.x)>5);
});

test('R008 nose width controls protrusion footprint and cast; eye spacing shapes the orbital field', () => {
  const a=deriveSurfaceField({noseWidth:80,eyeSpacing:-16,lightDirection:-60});
  const b=deriveSurfaceField({noseWidth:125,eyeSpacing:16,lightDirection:-60});
  assert.notEqual(a.values.noseLeft.shade,b.values.noseLeft.shade);
  assert.notEqual(a.noseCast.x,b.noseCast.x);
  assert.notEqual(a.values.orbitLeft.shade,b.values.orbitLeft.shade);
  assert.ok(a.face.anchors.leftEye.x>b.face.anchors.leftEye.x);
});

test('R008 CSS custom properties are finite and bound to real painter selectors', () => {
  const css=read('styles/study008.css');const app=read('src/app.mjs');
  const html=read('index.html');const standalone=read('standalone.html');
  for (const p of [defaults(),{jaw:118,eyeSpacing:16,lightDirection:-60,graphite:100,hatching:100},
                     {jaw:82,eyeSpacing:-16,lightDirection:60,graphite:15,hatching:0}]) {
    const style=deriveSurfaceFieldStyle(p);
    assert.equal(Object.keys(style).length,31);
    for(const value of Object.values(style))assert.doesNotMatch(value,/NaN|Infinity|url\(/);
    for(const k of ['noseLeft','noseRight','cheekLeft','cheekRight','orbitLeft','orbitRight']) {
      assert.ok(Number(style[`--v-${k}-shade`])>=0 && Number(style[`--v-${k}-shade`])<=.83);
    }
  }
  assert.match(css,/--sf-cast-x/);assert.match(css,/--sf-cast-center/);
  assert.match(css,/--sf-hatch-left-angle/);assert.match(css,/--sf-hatch-right-angle/);
  assert.match(css,/data-r008="field"/);
  assert.match(app,/surfaceVariant === 'field'/);assert.match(app,/deriveSurfaceFieldStyle\(values\)/);
  assert.match(html,/styles\/study008.css/);assert.match(html,/class="sf-nose-cast"/);
  assert.match(standalone,/Research 008: the R007 anchors/);
  assert.doesNotMatch(standalone,/href="\.\/study\/008-compare.html"/);
  assert.doesNotMatch(css,/<img|<svg|<canvas|url\s*\(/i);
});

test('R008 candidate is opt-in and does not modify existing character JSON contract', () => {
  const params=defaults();
  assert.equal(Object.keys(params).length,9);
  assert.deepEqual(decode(encode(params)),params);
  assert.doesNotMatch(encode(params),/r008|surfaceField|faceModel/);
  const app=read('src/app.mjs');
  assert.match(app,/if \(volumeStudy\) return/);
  assert.match(app,/if \(!researchEmbed && !volumeStudy\) restore\(\)/);
  const css=read('styles/study008.css');
  assert.match(css,/\.portrait \.(?:sf-nose-cast) \{display:none/);
  const study=read('study/008-compare.html');
  assert.match(study,/r008=legacy&amp;embed=1/);
  assert.match(study,/r008=field&amp;embed=1/);
  assert.match(study,/ART_UNVERIFIED/);
});
