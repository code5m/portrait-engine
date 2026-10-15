/**
 * Face DNA is the canonical structural description of a stylized 2.5D head.
 * The nine legacy sliders remain a reversible UI and export adapter, not a
 * second set of independent facial geometry state.
 */
import { normalize, defaults } from './parameters.mjs';

export const DEFAULT_FACE_DNA = Object.freeze({
  skull: Object.freeze({ width: .5, height: .5, forehead: .5 }),
  brow: Object.freeze({ height: .5, depth: .5, tilt: .5 }),
  orbit: Object.freeze({ depth: .5, width: .5, angle: .5 }),
  nose: Object.freeze({ bridge: .5, base: .5, projection: .5 }),
  cheek: Object.freeze({ height: .5, volume: .5 }),
  mouth: Object.freeze({ width: .5, volume: .5, corner: .5 }),
  jaw: Object.freeze({ width: .5, angle: .5 })
});

export function clamp01(value, fallback = .5) {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.min(1, Math.max(0, value)) : fallback;
}

function normalizeDNAGroup(source, fallback) {
  const result = {};
  for (const key of Object.keys(fallback)) result[key] = clamp01(source?.[key], fallback[key]);
  return result;
}

export function normalizeFaceDNA(input = {}) {
  const source = input && typeof input === 'object' && !Array.isArray(input) ? input : {};
  return Object.fromEntries(Object.entries(DEFAULT_FACE_DNA)
    .map(([name, group]) => [name, normalizeDNAGroup(source[name], group)]));
}

const dnaScale = (v, min, max) => clamp01((v - min) / (max - min));
const legacyScale = (v, min, max) => min + clamp01(v) * (max - min);

/** Convert validated old slider values to structural DNA without losing extra features. */
export function dnaFromLegacyParameters(input, prior = DEFAULT_FACE_DNA) {
  const p = normalize(input);
  const dna = normalizeFaceDNA(prior);
  dna.skull.width = dnaScale(p.faceWidth, 80, 120);
  dna.orbit.width = dnaScale(p.eyeSpacing, -16, 16);
  dna.nose.base = dnaScale(p.noseWidth, 80, 125);
  dna.jaw.width = dnaScale(p.jaw, 82, 118);
  dna.mouth.width = dnaScale(p.mouthWidth, 82, 118);
  return dna;
}

/** Adapter used by existing CSS primitives and v1 JSON export. */
export function legacyParametersFromDNA(input, finishing = defaults()) {
  const dna = normalizeFaceDNA(input);
  return normalize({
    ...finishing,
    faceWidth: legacyScale(dna.skull.width, 80, 120),
    eyeSpacing: legacyScale(dna.orbit.width, -16, 16),
    noseWidth: legacyScale(dna.nose.base, 80, 125),
    jaw: legacyScale(dna.jaw.width, 82, 118),
    mouthWidth: legacyScale(dna.mouth.width, 82, 118)
  });
}

export function deriveIdentityFingerprint(dna) {
  const d = normalizeFaceDNA(dna);
  return [
    d.skull.width, d.skull.height, d.orbit.depth, d.orbit.width,
    d.nose.projection, d.nose.base, d.cheek.volume, d.jaw.width,
    d.jaw.angle, d.mouth.width
  ].map(value => value.toFixed(3)).join('-');
}
