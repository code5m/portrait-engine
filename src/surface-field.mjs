/**
 * Research 008: continuous FACE-LOCAL relief and directional value probes.
 * This is a falsifiable 2.5D sketch hypothesis, not 3D anatomy/photogrammetry.
 * JavaScript returns geometry/light CSS variables; the DOM + CSS paint art.
 * It is gated behind ?r008=field; existing saved portraits remain untouched.
 */
import { normalize } from './parameters.mjs';
import { deriveFaceGeometry } from './face-model.mjs';
import { lightVector } from './volume.mjs';

const clampField = (x, min = 0, max = 1) => Math.min(max, Math.max(min, x));
const gaussian = (x, y, cx, cy, sx, sy) =>
  Math.exp(-0.5 * (((x-cx)/sx)**2 + ((y-cy)/sy)**2));
const rad = degrees => degrees * Math.PI / 180;

/** Signed relief in logical face pixels. Higher numbers protrude toward viewer. */
export function deriveRelief(raw) {
  const p = normalize(raw);
  const face = deriveFaceGeometry(p);
  const a = face.anchors;
  const lobes = [
    // The same landmarks that position CSS organs define the depth field.
    [a.leftBrow, 7, 29, 16], [a.rightBrow, 7, 29, 16],
    [a.leftOrbit, -13, 27, 20], [a.rightOrbit, -13, 27, 20],
    [a.noseRoot, 15, 20, 52], [a.noseBase, 13, 19 * p.noseWidth/100, 16],
    [a.leftAla, 5, 14, 12], [a.rightAla, 5, 14, 12],
    [a.leftCheek, 10, 30, 35], [a.rightCheek, 10, 30, 35],
    [a.leftJaw, -3, 27, 31], [a.rightJaw, -3, 27, 31],
    [a.mouth, 4, 40 * p.mouthWidth/100, 15],
    [a.chin, 6, 32, 24]
  ];
  const heightAt = (x, y) => lobes.reduce((sum, [c, h, sx, sy]) =>
    sum + h * gaussian(x, y, c.x, c.y, sx, sy), 0);
  // Analytic finite differences, not pixels sampled from a screenshot.
  const normalAt = (x, y) => {
    const dx = (heightAt(x + 1, y) - heightAt(x - 1, y)) / 2;
    const dy = (heightAt(x, y + 1) - heightAt(x, y - 1)) / 2;
    // The CSS face is horizontally stretched by faceScale; compensate the
    // local x-slope in world coordinates so width changes alter shading.
    const v = [-2.0 * dx / face.faceScale, -2.0 * dy, 1];
    const magnitude = Math.hypot(...v);
    return Object.freeze(v.map(n => n / magnitude));
  };
  return Object.freeze({ face, heightAt, normalAt });
}

/** Distinct shading probes at the flanks, not the feature's geometric center. */
export function deriveSurfaceField(raw) {
  const p = normalize(raw);
  const field = deriveRelief(p);
  const a = field.face.anchors;
  const points = {
    browLeft: [a.leftBrow.x - 9, a.leftBrow.y + 7],
    browRight: [a.rightBrow.x + 9, a.rightBrow.y + 7],
    orbitLeft: [a.leftOrbit.x - 13, a.leftOrbit.y + 5],
    orbitRight: [a.rightOrbit.x + 13, a.rightOrbit.y + 5],
    noseLeft: [a.leftAla.x - 6, a.noseBase.y - 20],
    noseRight: [a.rightAla.x + 6, a.noseBase.y - 20],
    cheekLeft: [a.leftCheek.x - 17, a.leftCheek.y + 6],
    cheekRight: [a.rightCheek.x + 17, a.rightCheek.y + 6],
    jawLeft: [a.leftJaw.x - 10, a.leftJaw.y - 7],
    jawRight: [a.rightJaw.x + 10, a.rightJaw.y - 7],
    chin: [a.chin.x, a.chin.y - 9],
    forehead: [(a.leftBrow.x + a.rightBrow.x) / 2, a.leftBrow.y - 56]
  };
  const light = lightVector(p.lightDirection);
  const values = {};
  for (const [region, [x, y]] of Object.entries(points)) {
    const normal = field.normalAt(x, y);
    const diffuse = clampField(normal.reduce((sum, n, i) => sum + n * light[i], 0));
    const tone = 0.18 + (1 - diffuse) * 0.96;
    const shade = clampField(tone * (0.3 + 0.7 * p.graphite / 100), 0.05, 0.83);
    values[region] = Object.freeze({ normal, diffuse, shade,
      lightness: clampField(diffuse**3 * (0.23 - p.graphite / 900)) });
  }
  const degrees = p.lightDirection;
  const castX = -Math.sin(rad(degrees)) * (14 + p.noseWidth * 0.06);
  const noseCast = Object.freeze({
    x: castX,
    y: a.noseBase.y + 2,
    centerX: a.noseBase.x,
    opacity: clampField((0.10 + 0.20 * Math.abs(Math.sin(rad(degrees)))) * (p.graphite / 100), 0.02, 0.35)
  });
  const cheekAngle = (side) => {
    const c = side === 'left' ? a.leftCheek : a.rightCheek;
    const j = side === 'left' ? a.leftJaw : a.rightJaw;
    return Math.atan2(j.y - c.y, j.x - c.x) * 180 / Math.PI;
  };
  return Object.freeze({
    values: Object.freeze(values), noseCast,
    cheekAngles: Object.freeze({left: cheekAngle('left'), right: cheekAngle('right')}),
    face: field.face
  });
}

export function deriveSurfaceFieldStyle(raw) {
  const p = normalize(raw);
  const field = deriveSurfaceField(p);
  const css = {};
  for (const [name, value] of Object.entries(field.values)) {
    css[`--v-${name}-shade`] = value.shade.toFixed(4);
    css[`--v-${name}-light`] = value.lightness.toFixed(4);
  }
  css['--sf-cast-x'] = `${field.noseCast.x.toFixed(2)}px`;
  css['--sf-cast-y'] = `${field.noseCast.y.toFixed(2)}px`;
  css['--sf-cast-center'] = `${field.noseCast.centerX.toFixed(2)}px`;
  css['--sf-cast-opacity'] = field.noseCast.opacity.toFixed(4);
  css['--sf-hatch-left-angle'] = `${field.cheekAngles.left.toFixed(2)}deg`;
  css['--sf-hatch-right-angle'] = `${field.cheekAngles.right.toFixed(2)}deg`;
  css['--sf-hatch-opacity'] = (p.hatching / 100 * .18).toFixed(4);
  return Object.freeze(css);
}
