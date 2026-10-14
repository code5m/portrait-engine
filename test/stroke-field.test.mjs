import test from 'node:test';
import assert from 'node:assert/strict';
import { defaults, encode, decode } from '../src/parameters.mjs';
import { deriveStrokeField, deriveStrokeFieldStyle, STROKE_REGIONS } from '../src/stroke-field.mjs';

const base = defaults();
test('R009 has exactly 11 local strokes, numeric and bounded', () => {
  const result=deriveStrokeField(base);
  assert.equal(Object.keys(result).length,11);
  assert.equal(STROKE_REGIONS.length,11);
  for(const region of STROKE_REGIONS){
    assert.ok(result[region].angle >= 0 && result[region].angle < 180, region);
    assert.ok(result[region].opacity >= 0 && result[region].opacity <= .39, region);
    assert.ok(Number.isFinite(result[region].shade));
  }
});
test('R009 dark side gets stronger hatching when key light reverses',()=>{
  const left=deriveStrokeField({...base,lightDirection:-60,hatching:100});
  const right=deriveStrokeField({...base,lightDirection:60,hatching:100});
  assert.ok(left.cheekLeft.opacity < left.cheekRight.opacity);
  assert.ok(right.cheekLeft.opacity > right.cheekRight.opacity);
  for(const name of STROKE_REGIONS)
    assert.equal(left[name].angle,right[name].angle,'direction follows geometry, not the light');
});
test('R009 zero pencil density removes all research strokes',()=>{
  for(const s of Object.values(deriveStrokeField({...base,hatching:0}))) assert.equal(s.opacity,0);
});
test('R009 geometry, including jaw change, alters tangent orientation',()=>{
  const a=deriveStrokeField({...base,jaw:82});
  const b=deriveStrokeField({...base,jaw:118});
  const moved=STROKE_REGIONS.some(region=>Math.abs(a[region].angle-b[region].angle)>.05);
  assert.ok(moved, 'at least one stroke tangent must move with jaw geometry');
});
test('R009 clamp/serialized v1 compatibility; no new persisted keys',()=>{
  const old={format:'portrait-engine-params',version:1,parameters:{faceWidth:95,eyeSpacing:2,jaw:110,graphite:60,hatching:60,hairVolume:95,noseWidth:100}};
  const normalized=decode(JSON.stringify(old));
  assert.deepEqual(decode(encode(normalized)), normalized);
  assert.equal(Object.keys(normalized).length,9);
  const css=deriveStrokeFieldStyle({...normalized,lightDirection:999,hatching:-5});
  assert.equal(Object.keys(css).length,22);
  for(const val of Object.values(css)) assert.ok(/^[-\d.]+(deg)?$/.test(val));
});
