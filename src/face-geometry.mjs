/**
 * Research 011: Face DNA -> geometry layer.
 *
 * This module separates identity description from rendering.
 * It produces stable 2D landmarks consumed by a future renderer.
 */

import { normalizeFaceDNA, DEFAULT_FACE_DNA } from './face-dna.mjs';

export function deriveFaceGeometry(input = DEFAULT_FACE_DNA) {
  const dna = normalizeFaceDNA(input);
  const skullWidth = 200 + (dna.skull.width - 0.5) * 70;
  const skullHeight = 250 + (dna.skull.height - 0.5) * 80;
  const eyeDepth = 18 + dna.orbit.depth * 14;
  const jawWidth = 120 + dna.jaw.width * 70;

  return Object.freeze({
    skull: {
      width: round(skullWidth),
      height: round(skullHeight),
      foreheadCurve: round(dna.skull.forehead * 100)
    },
    orbit: {
      left: { x: 100, depth: round(eyeDepth) },
      right: { x: 200, depth: round(eyeDepth) },
      tilt: round((dna.orbit.angle - 0.5) * 12)
    },
    nose: {
      bridge: round(40 + dna.nose.bridge * 30),
      projection: round(dna.nose.projection * 40)
    },
    cheek: {
      height: round(120 + dna.cheek.height * 50),
      volume: round(dna.cheek.volume * 100)
    },
    mouth: {
      width: round(50 + dna.mouth.width * 40),
      corner: round((dna.mouth.corner - 0.5) * 10)
    },
    jaw: {
      width: round(jawWidth),
      angle: round(dna.jaw.angle * 90)
    }
  });
}

function round(value) {
  return Number(value.toFixed(2));
}
