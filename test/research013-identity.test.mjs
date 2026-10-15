import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { IDENTITIES } from '../src/identity/identity-registry.mjs';
import { deriveContourStations, contourWidthAt, deriveContourPolygon, deriveIdentityFormStyle, identityMorphSignature } from '../src/anatomy/identity-contour.mjs';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('three preset identities have distinct structural CSS contours, not just distinct numeric fingerprints',()=>{
  const poly=IDENTITIES.map(i=>deriveContourPolygon(i.faceDNA));
  const signature=IDENTITIES.map(i=>identityMorphSignature(i.faceDNA));
  assert.equal(new Set(poly).size,3);
  assert.equal(new Set(signature).size,3);
});
test('contour is symmetric, bounded and smoothly sampled for arbitrary DNA',()=>{
  for(const identity of IDENTITIES){
    const stations=deriveContourStations(identity.faceDNA);
    assert.equal(stations.length,13);
    assert.ok(stations.every((s,i)=>s.width>=3&&s.width<=49&&(i===0||stations[i-1].y<s.y)));
    for(let y=0;y<=100;y+=.5)assert.ok(contourWidthAt(stations,y)>=3);
    const polygon=deriveContourPolygon(identity.faceDNA);
    assert.equal((polygon.match(/%/g)||[]).length,204);
    assert.ok(!polygon.includes('NaN'));
  }
});
test('jaw and cheek mutation changes contour, whereas light changes shading but not silhouette',()=>{
 const d=IDENTITIES[0].faceDNA;
 const jaw={...d,jaw:{...d.jaw,width:1}};
 const cheek={...d,cheek:{...d.cheek,volume:1}};
 assert.notEqual(deriveContourPolygon(d),deriveContourPolygon(jaw));
 assert.notEqual(deriveContourPolygon(d),deriveContourPolygon(cheek));
 const front=deriveIdentityFormStyle(d,{mode:'front'});
 const side=deriveIdentityFormStyle(d,{mode:'side'});
 assert.equal(front['--r013-head-contour'],side['--r013-head-contour']);
 assert.notEqual(front['--r013-shadow-center'],side['--r013-shadow-center']);
});
test('candidate remains explicitly opt-in, CSS-only and research default untouched',()=>{
 const css=read('styles/research013.css'),app=read('src/app.mjs'),html=read('index.html');
 assert.match(css,/\[data-r013="anatomy"\]/);
 assert.doesNotMatch(css,/(url\s*\(|data:image|<svg|<canvas|<img)/i);
 assert.match(app,/qs\.get\('r013'\) === 'anatomy'/);
 assert.match(html,/styles\/research013\.css/);
});
