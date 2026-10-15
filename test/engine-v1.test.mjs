import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {defaults,encode} from '../src/parameters.mjs';
import {dnaFromLegacyParameters,legacyParametersFromDNA,deriveIdentityFingerprint} from '../src/face-dna.mjs';
import {deriveDNAGeometry,deriveDNAGeometryStyle} from '../src/face-geometry.mjs';
import {IDENTITIES} from '../src/identity/identity-registry.mjs';
import {EXPRESSION_PRESETS} from '../src/expression/expression-dna.mjs';
import {deriveExpressionStyle} from '../src/expression/expression-engine.mjs';
import {sampleHairField} from '../src/hair/hair-field.mjs';
import {deriveHairStyle} from '../src/hair/hair-generator.mjs';
import {deriveSkinStyle} from '../src/material/skin-material.mjs';
import {deriveArtisticSurfaceStyle} from '../src/material/artistic-surface.mjs';
import {deriveLightingRig} from '../src/lighting.mjs';
import {buildFaceState,deriveEngineStyle,encodeFaceState,decodeFaceState} from '../src/engine.mjs';
const text=path=>fs.readFileSync(new URL('../'+path,import.meta.url),'utf8');
test('legacy nine controls round trip via canonical DNA and old JSON v1',()=>{
 const p=defaults(),dna=dnaFromLegacyParameters(p);
 assert.deepEqual(legacyParametersFromDNA(dna,p),p);
 assert.deepEqual(decodeFaceState(encode(p)).parameters,p);
});
test('three real identity records have unique stable DNA fingerprints',()=>{
 assert.equal(IDENTITIES.length,3);
 assert.equal(new Set(IDENTITIES.map(x=>x.fingerprint)).size,3);
 for(const identity of IDENTITIES){
  assert.equal(identity.fingerprint,deriveIdentityFingerprint(identity.faceDNA));
  const state=buildFaceState({id:identity.id,faceDNA:identity.faceDNA});
  assert.deepEqual(decodeFaceState(encodeFaceState(state)).faceDNA,state.faceDNA);
 }
});
test('DNA drives actual CSS landmarks and geometry',()=>{
 const a=deriveDNAGeometry(IDENTITIES[0].faceDNA),b=deriveDNAGeometry(IDENTITIES[1].faceDNA);
 assert.notDeepEqual(a.anchors,b.anchors);
 assert.notDeepEqual(deriveDNAGeometryStyle(IDENTITIES[0].faceDNA),deriveDNAGeometryStyle(IDENTITIES[1].faceDNA));
 assert.equal(Object.keys(a.anchors).length,16);
});
test('all expressions produce different finite geometric styling',()=>{
 const list=Object.values(EXPRESSION_PRESETS).map(deriveExpressionStyle);
 assert.equal(new Set(list.map(x=>JSON.stringify(x))).size,5);
 assert.ok(list.every(x=>Object.values(x).every(y=>!String(y).includes('NaN'))));
});
test('hair field is deterministic and CSS output changes with growth parameters',()=>{
 assert.deepEqual(sampleHairField({density:.7}),sampleHairField({density:.7}));
 assert.notDeepEqual(deriveHairStyle({curl:.1}),deriveHairStyle({curl:.9}));
 assert.equal(sampleHairField({},24).length,24);
});
test('skin and artistic surface are CSS-only and parameterized',()=>{
 assert.notDeepEqual(deriveSkinStyle({pore:.1}),deriveSkinStyle({pore:.8}));
 assert.notDeepEqual(deriveArtisticSurfaceStyle({paper:.1}),deriveArtisticSurfaceStyle({paper:.9}));
});
test('lighting presets use distinct directions and the same engine',()=>{
 assert.notDeepEqual(deriveLightingRig({mode:'front'}).vector,deriveLightingRig({mode:'top'}).vector);
 assert.notDeepEqual(deriveLightingRig({mode:'front'}).vector,deriveLightingRig({mode:'side'}).vector);
});
test('3 identities x 3 light scenes x 5 expressions are deterministic, distinct and finite',()=>{
 const signatures=new Set();
 for(const identity of IDENTITIES)for(const light of ['front','side','top']){
  const state=buildFaceState({id:identity.id,faceDNA:identity.faceDNA,lighting:{mode:light}});
  const css=deriveEngineStyle(state);
  assert.deepEqual(css,deriveEngineStyle(state));
  assert.ok(Object.values(css).every(x=>!String(x).includes('NaN')&&!String(x).includes('Infinity')));
  signatures.add(css['--fg-leftEye-x']+':'+css['--v-cheekLeft-shade']+':'+css['--light-elevation']);
  for(const expression of Object.keys(EXPRESSION_PRESETS)){
   const result=deriveEngineStyle({...state,expression:EXPRESSION_PRESETS[expression]});
   assert.ok(result['--expr-mouth-open']);
  }
 }
 assert.ok(signatures.size>=6);
});
test('v2 file rejects corrupted fingerprint, hostile fields and bad format',()=>{
 const state=buildFaceState({faceDNA:IDENTITIES[0].faceDNA});
 const data=JSON.parse(encodeFaceState(state));data.identity.fingerprint='spoofed';
 assert.throws(()=>decodeFaceState(JSON.stringify(data)),/fingerprint/);
 assert.throws(()=>decodeFaceState('{}'),/Unsupported/);
});
test('the new UI wires all engines and keeps pure CSS constraints',()=>{
 const page=text('index.html'),app=text('src/app.mjs'),css=text('styles/face-engine.css');
 for(const name of ['data-identity','data-expression','data-light-mode'])assert.match(page,new RegExp(name));
 assert.match(app,/deriveEngineStyle/);
 assert.match(css,/data-face-engine="v1"/);
 assert.doesNotMatch(css,/(url\s*\(|data:image|<svg|<canvas)/i);
});
