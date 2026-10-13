import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFINITIONS, PRESETS, KEYS, defaults, normalize, encode, decode, equal } from '../src/parameters.mjs';

test('presets have finite, valid values', () => {
  for (const config of Object.values(PRESETS)) {
    assert.deepEqual(Object.keys(config).sort(), [...KEYS].sort());
    assert.deepEqual(normalize(config), config);
  }
});
test('values clamp to ranges; non-numbers are rejected', () => {
  const result = normalize({ faceWidth: 9000, eyeSpacing: -999, noseWidth: Infinity, jaw: '20', graphite: NaN, hairVolume: 75, hatching: -7 });
  assert.equal(result.faceWidth, DEFINITIONS.faceWidth.max);
  assert.equal(result.eyeSpacing, DEFINITIONS.eyeSpacing.min);
  assert.equal(result.noseWidth, defaults().noseWidth);
  assert.equal(result.jaw, defaults().jaw);
  assert.equal(result.hatching, DEFINITIONS.hatching.min);
  assert.equal(result.hairVolume, 75);
});
test('JSON export round-trips every preset', () => {
  for (const config of Object.values(PRESETS)) assert.deepEqual(decode(encode(config)), config);
});
test('bad JSON and unsupported protocol fail safely', () => {
  for (const bad of ['not json', '{}', '{"version":3}', '{"format":"portrait-engine-params","version":1,"parameters":{"faceWidth":"no"}}']) assert.throws(() => decode(bad));
});
test('unknown keys do not pollute prototypes', () => {
  const parsed = JSON.parse('{"faceWidth":91,"__proto__":{"injected":true}}');
  const result = normalize(parsed);
  assert.equal(result.faceWidth, 91);
  assert.equal(result.injected, undefined);
  assert.equal({}.injected, undefined);
});
test('value equality, not object identity, determines active preset', () => {
  assert.equal(equal(defaults(), { ...defaults() }), true);
  assert.equal(equal(defaults(), { ...defaults(), faceWidth: 101 }), false);
});
