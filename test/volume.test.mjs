import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { PLANE_NORMALS, lightVector, deriveVolumeValues, deriveVolumeStyle } from '../src/volume.mjs';
import { defaults, decode, encode } from '../src/parameters.mjs';

const read=name=>fs.readFileSync(new URL(`../${name}`,import.meta.url),'utf8');
test('R006 planes share normalized physical-inspired light direction and bounded values',()=>{
  assert.equal(Object.keys(PLANE_NORMALS).length,12);
  for(const vector of Object.values(PLANE_NORMALS)) {
    assert.equal(vector.length,3);
    assert.ok(vector.every(Number.isFinite));
  }
  for(const angle of [-60,0,60]) {
    assert.ok(Math.abs(Math.hypot(...lightVector(angle))-1)<1e-10);
    assert.deepEqual(lightVector(Number.NaN), lightVector(0));
    for(const p of Object.values(deriveVolumeValues({...defaults(),lightDirection:angle}))){
      assert.ok(p.diffuse>=0 && p.diffuse<=1);
      assert.ok(p.shade>=0 && p.shade<=1);
      assert.ok(p.lightness>=0 && p.lightness<=1);
    }
  }
});
test('lights change both cheeks and both nose planes coherently, not independently',()=>{
  const left=deriveVolumeValues({...defaults(),lightDirection:-60});
  const front=deriveVolumeValues({...defaults(),lightDirection:0});
  const right=deriveVolumeValues({...defaults(),lightDirection:60});
  for(const part of ['cheek','brow','orbit','nose','jaw']) {
    assert.ok(left[`${part}Left`].shade<left[`${part}Right`].shade, `${part} left under -60`);
    assert.ok(right[`${part}Right`].shade<right[`${part}Left`].shade,`${part} right under +60`);
    assert.ok(Math.abs(front[`${part}Left`].shade-front[`${part}Right`].shade)<1e-10);
  }
});
test('no CSS painter calls, no image dependencies, stable bounded style protocol',()=>{
  const css=read('styles/study006.css');
  const app=read('src/app.mjs');
  const index=read('index.html');
  const built=read('standalone.html');
  const output=deriveVolumeStyle({...defaults(),lightDirection:120,graphite:999});
  assert.match(css, /data-r006="volume"/);
  assert.doesNotMatch(css,/url\s*\(|<svg|<canvas|<img|data:image/i);
  assert.match(index,/href="\.\/styles\/study006\.css"/);
  assert.match(index,/class="volume-field"/);
  assert.match(built,/Research 006 \/ opt-in surface-value experiment/);
  assert.match(app,/volumeVariant === 'volume'/);
  assert.match(app,/if \(!researchEmbed && !volumeStudy\) restore\(\)/);
  assert.match(app,/if \(volumeStudy\) return/);
  assert.equal(output["--v-hatch-strength"], "0.6200");
  assert.ok(Object.values(output).every(v=>typeof v==='string'));
});
test('old 7-key and 9-key portraits still roundtrip without research state',()=>{
  const old={faceWidth:92,eyeSpacing:3,noseWidth:107,jaw:101,hatching:70,graphite:46,hairVolume:120};
  const nine=decode(JSON.stringify({format:'portrait-engine-params',version:1,parameters:old}));
  assert.equal(nine.faceWidth,92);
  assert.equal(nine.mouthWidth,100);
  assert.equal(nine.lightDirection,-30);
  const fresh=decode(encode({...nine,mouthWidth:108,lightDirection:50}));
  assert.equal(fresh.mouthWidth,108);
  assert.equal(fresh.lightDirection,50);
  assert.equal(Object.keys(fresh).length,9);
});

test('Research 006 comparison remains local and separated from the public portrait',()=>{
  const html=read('study/006-compare.html');
  assert.match(html,/r006=baseline&amp;embed=1/);
  assert.match(html,/r006=volume&amp;embed=1/);
  assert.match(html,/尚未|没有实际真人盲评结果/);
  assert.doesNotMatch(html,/<img\b|<svg\b|<canvas\b|https?:\/\//i);
});
