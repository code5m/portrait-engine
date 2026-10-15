/**
 * R013: falsifiable structural identity hypothesis.
 *
 * Existing DNA moves 16 landmarks, but the fixed oval and same organ scale
 * make different people look like the same puppet. This module produces a
 * 2D CSS silhouette and coherent facial proportions from immutable DNA.
 *
 * No external images, SVG paths, Canvas pixels, random noise or DOM state.
 * This is not measured medical anatomy or evidence of photorealism.
 */
import { normalizeFaceDNA } from '../face-dna.mjs';
import { deriveDNAGeometry } from '../face-geometry.mjs';
import { deriveLightingRig } from '../lighting.mjs';

const round = (value, digits = 3) => Number(value.toFixed(digits));
const deviation = value => value - .5;
const between = (value, min, max) => Math.min(max, Math.max(min, value));

/** Station widths are the half-width of a head in a 207 x 304 CSS plane. */
export function deriveContourStations(input) {
  const d = normalizeFaceDNA(input);
  const skull = deviation(d.skull.width), cheek = deviation(d.cheek.volume);
  const jaw = deviation(d.jaw.width), angle = deviation(d.jaw.angle);
  const height = deviation(d.skull.height);
  return Object.freeze([
    [0, 9],
    [5, 24 + skull * 4],
    [13, 38 + skull * 7],
    [24, 45 + skull * 7],
    [36, 48 + skull * 8],
    [48, 48 + skull * 5 + cheek * 2],
    [59, 47 + cheek * 9],
    [68, 44 + cheek * 5 + jaw * 4],
    [76, 39 + jaw * 12 + angle * 2],
    [84, 33 + jaw * 13 + angle * 5],
    [91, 26 + jaw * 10 + angle * 4],
    [96, 17 + jaw * 5 + height * 2],
    [100, 5 + jaw * 2]
  ].map(([y, width]) => Object.freeze({ y, width: round(between(width, 3, 49), 2) })));
}

const smooth = t => t * t * (3 - 2 * t);
export function contourWidthAt(stations, y) {
  const height = between(y, 0, 100);
  if (height <= stations[0].y) return stations[0].width;
  for (let i = 1; i < stations.length; ++i) {
    if (height <= stations[i].y) {
      const a = stations[i - 1], b = stations[i];
      const f = smooth((height - a.y) / (b.y - a.y));
      return a.width + (b.width - a.width) * f;
    }
  }
  return stations[stations.length - 1].width;
}

/** 2%-height contour sampling has small enough segments to avoid big facets. */
export function deriveContourPolygon(input, step = 2) {
  const stations = deriveContourStations(input);
  const n = between(Math.round(100 / between(step, 1, 10)), 10, 100);
  const y = Array.from({ length: n + 1 }, (_, i) => 100 * i / n);
  const left = y.map(t =>
    round(50 - contourWidthAt(stations, t), 2) + '% ' + round(t, 2) + '%');
  const right = y.slice().reverse().map(t =>
    round(50 + contourWidthAt(stations, t), 2) + '% ' + round(t, 2) + '%');
  return 'polygon(' + left.concat(right).join(', ') + ')';
}

/** Only the opt-in R013 CSS consumes these variables. */
export function deriveIdentityFormStyle(input, lighting = { mode: 'front' }) {
  const dna = normalizeFaceDNA(input);
  const g = deriveDNAGeometry(dna);
  const rig = deriveLightingRig(lighting);
  const orbit = deviation(dna.orbit.depth), cheek = deviation(dna.cheek.volume);
  const x = rig.vector[0];
  return Object.freeze({
    '--r013-head-contour': deriveContourPolygon(dna),
    '--r013-eye-scale-x': String(round(.94 + deviation(dna.orbit.width) * .32)),
    '--r013-eye-scale-y': String(round(.94 - orbit * .22)),
    '--r013-brow-scale': String(round(.97 + deviation(dna.brow.depth) * .3)),
    '--r013-nose-scale-x': String(round(.95 + deviation(dna.nose.base) * .52)),
    '--r013-nose-scale-y': String(round(.95 + deviation(dna.nose.projection) * .28)),
    '--r013-mouth-scale-x': String(round(.96 + deviation(dna.mouth.width) * .34)),
    '--r013-mouth-scale-y': String(round(.94 + deviation(dna.mouth.volume) * .24)),
    '--r013-malar-intensity': String(round(.32 + cheek * .2)),
    '--r013-jaw-intensity': String(round(.34 + deviation(dna.jaw.angle) * .25)),
    '--r013-shadow-center': round(between(50 - x * 45, 23, 77), 1) + '%',
    '--r013-shadow-opacity': String(round(.16 + Math.abs(x) * .15)),
    '--r013-orbit-intensity': String(round(.32 + orbit * .21)),
    '--r013-geometry-distance': String(round(Math.abs(g.anchors.leftJaw.x - g.anchors.rightJaw.x), 2))
  });
}

/** Capture structural identity without lighting or visual presentation. */
export function identityMorphSignature(input) {
  const d = normalizeFaceDNA(input);
  const g = deriveDNAGeometry(d);
  const stations = deriveContourStations(d);
  const terms = [
    ...stations.filter((_, i) => i % 2 === 0).map(s => s.width),
    g.anchors.leftEye.x, g.anchors.rightEye.x,
    g.anchors.noseBase.y, g.anchors.leftJaw.x, g.anchors.rightJaw.x,
    d.orbit.depth, d.nose.projection, d.mouth.width
  ];
  return terms.map(v => round(v, 3)).join(':');
}
