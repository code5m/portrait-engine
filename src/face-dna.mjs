/**
 * Research 011: Face DNA structural model.
 *
 * This module intentionally does not render pixels. It describes human-like
 * face relationships before the CSS renderer consumes them.
 * It is an experimental 2D portrait abstraction, not a medical anatomy model.
 */

export const DEFAULT_FACE_DNA = Object.freeze({
  skull: Object.freeze({ width: 1, height: 1, forehead: 0.5 }),
  brow: Object.freeze({ height: 0.5, depth: 0.5, tilt: 0 }),
  orbit: Object.freeze({ depth: 0.5, width: 0.5, angle: 0 }),
  nose: Object.freeze({ bridge: 0.5, base: 0.5, projection: 0.5 }),
  cheek: Object.freeze({ height: 0.5, volume: 0.5 }),
  mouth: Object.freeze({ width: 0.5, volume: 0.5, corner: 0 }),
  jaw: Object.freeze({ width: 0.5, angle: 0.5 })
});

export function clamp01(value, fallback = 0.5) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(1, Math.max(0, number));
}

export function normalizeFaceDNA(input = {}) {
  return {
    skull: normalizeGroup(input.skull, DEFAULT_FACE_DNA.skull),
    brow: normalizeGroup(input.brow, DEFAULT_FACE_DNA.brow),
    orbit: normalizeGroup(input.orbit, DEFAULT_FACE_DNA.orbit),
    nose: normalizeGroup(input.nose, DEFAULT_FACE_DNA.nose),
    cheek: normalizeGroup(input.cheek, DEFAULT_FACE_DNA.cheek),
    mouth: normalizeGroup(input.mouth, DEFAULT_FACE_DNA.mouth),
    jaw: normalizeGroup(input.jaw, DEFAULT_FACE_DNA.jaw)
  };
}

function normalizeGroup(source, defaults) {
  const output = {};
  for (const key of Object.keys(defaults)) {
    output[key] = clamp01(source?.[key], defaults[key]);
  }
  return output;
}

export function deriveIdentityFingerprint(dna) {
  const value = normalizeFaceDNA(dna);
  return [
    value.skull.width,
    value.orbit.depth,
    value.nose.projection,
    value.cheek.volume,
    value.jaw.width,
    value.mouth.corner
  ].map(number => number.toFixed(2)).join('-');
}
