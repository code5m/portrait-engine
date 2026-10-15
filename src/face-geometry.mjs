/**
 * Canonical DNA -> 16 existing face-local CSS landmarks and extra 2.5D metrics.
 * This is an artistic approximation, not a 3D mesh or biometric identity.
 */
import { normalizeFaceDNA, legacyParametersFromDNA } from './face-dna.mjs';
import { deriveFaceGeometry } from './face-model.mjs';

const dnaRound = value => Number(value.toFixed(2));
const dnaOffset = value => value - .5;

export function deriveDNAGeometry(input) {
  const dna = normalizeFaceDNA(input);
  const legacy = deriveFaceGeometry(legacyParametersFromDNA(dna));
  const a = Object.fromEntries(Object.entries(legacy.anchors)
    .map(([name, p]) => [name, { x: p.x, y: p.y }]));
  const browShift = -dnaOffset(dna.brow.height) * 20;
  const orbitShift = dnaOffset(dna.orbit.depth) * 8;
  const tilt = dnaOffset(dna.orbit.angle) * 10;
  for (const side of ['left', 'right']) {
    const sign = side === 'left' ? -1 : 1;
    for (const name of ['Eye','Orbit']) a[side + name].y += orbitShift + sign * tilt;
    a[side + 'Brow'].y += browShift + sign * tilt;
    a[side + 'Cheek'].y -= dnaOffset(dna.cheek.height) * 18;
    a[side + 'Cheek'].x += sign * dnaOffset(dna.cheek.volume) * 13;
    a[side + 'Jaw'].y += dnaOffset(dna.jaw.angle) * 8;
  }
  a.noseRoot.y -= dnaOffset(dna.nose.bridge) * 14;
  a.noseBase.y += dnaOffset(dna.nose.projection) * 12;
  a.leftAla.y += dnaOffset(dna.nose.projection) * 12;
  a.rightAla.y += dnaOffset(dna.nose.projection) * 12;
  a.mouth.y += dnaOffset(dna.mouth.volume) * 10;
  a.chin.y += dnaOffset(dna.skull.height) * 18;
  for (const point of Object.values(a)) {
    point.x = dnaRound(point.x);
    point.y = dnaRound(point.y);
    Object.freeze(point);
  }
  return Object.freeze({
    frame: legacy.frame, faceScale: legacy.faceScale, anchors: Object.freeze(a),
    metrics: Object.freeze({
      skullHeight: dnaRound(.96 + dnaOffset(dna.skull.height) * .19),
      orbitDepth: dnaRound(dna.orbit.depth),
      browDepth: dnaRound(dna.brow.depth),
      noseProjection: dnaRound(dna.nose.projection),
      cheekVolume: dnaRound(dna.cheek.volume),
      mouthCorner: dnaRound(dna.mouth.corner)
    })
  });
}

export function deriveDNAGeometryStyle(input) {
  const geometry = deriveDNAGeometry(input);
  const style = {};
  for (const [name, point] of Object.entries(geometry.anchors)) {
    style['--fg-' + name + '-x'] = point.x.toFixed(2) + 'px';
    style['--fg-' + name + '-y'] = point.y.toFixed(2) + 'px';
  }
  style['--dna-skull-height'] = String(geometry.metrics.skullHeight);
  style['--dna-orbit-depth'] = String(geometry.metrics.orbitDepth);
  style['--dna-brow-depth'] = String(geometry.metrics.browDepth);
  style['--dna-nose-projection'] = String(geometry.metrics.noseProjection);
  style['--dna-cheek-volume'] = String(geometry.metrics.cheekVolume);
  style['--dna-mouth-corner'] = String(geometry.metrics.mouthCorner);
  return Object.freeze(style);
}
