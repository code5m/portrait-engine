/**
 * Research 007 / FaceGeometry v0 (2D structural landmark proposal).
 *
 * One FACE-LOCAL reference frame (207 x 304 logical pixels) anchors the
 * orbit, nose, cheek, mouth and jaw. All painting stays native HTML/CSS.
 * In particular, this is NOT a skull mesh, medical anatomy, or likeness model.
 * Local coordinates inherit the existing .face scaleX when painted.
 */
import { normalize } from './parameters.mjs';

const FRAME = Object.freeze({ x: 87, y: 91, width: 207, height: 304, centerX: 103.5 });
const point = (x, y) => Object.freeze({ x, y });
const lerp = (a, b, t) => a + (b - a) * t;

export function deriveFaceGeometry(raw) {
  const p = normalize(raw);
  const eyeL = point(55.5 - p.eyeSpacing, 157);
  const eyeR = point(149.5 + p.eyeSpacing, 158);
  // Nose lies on the midline between both orbits; width moves BOTH alae.
  const mid = (eyeL.x + eyeR.x) / 2 + 1;
  const noseRoot = point(mid, lerp(eyeL.y, eyeR.y, .5) + 11.5);
  const noseBase = point(mid + .5, noseRoot.y + 70);
  const alaSpan = 18 * p.noseWidth / 100;
  // The malar plane is defined between the orbit and mandibular turn.
  const jawSpread = 1 + (p.jaw - 100) * .009;
  const leftJaw = point(mid - 63 * jawSpread, 257 + (p.jaw - 100) * .08);
  const rightJaw = point(mid + 63 * jawSpread, 258 + (p.jaw - 100) * .08);
  const leftCheek = point(lerp(eyeL.x, leftJaw.x, .59), lerp(eyeL.y, leftJaw.y, .35));
  const rightCheek = point(lerp(eyeR.x, rightJaw.x, .59), lerp(eyeR.y, rightJaw.y, .35));
  const chin = point(lerp(leftJaw.x, rightJaw.x, .5), 285 + (p.jaw - 100) * .06);
  const mouth = point(lerp(noseBase.x, chin.x, .34), lerp(noseBase.y, chin.y, .44));

  const anchors = Object.freeze({
    leftEye: eyeL,
    rightEye: eyeR,
    leftBrow: point(eyeL.x - 2, eyeL.y - 38),
    rightBrow: point(eyeR.x + 1, eyeR.y - 39),
    leftOrbit: point(eyeL.x, eyeL.y - 3),
    rightOrbit: point(eyeR.x, eyeR.y - 3),
    noseRoot,
    noseBase,
    leftAla: point(noseBase.x - alaSpan, noseBase.y - 2),
    rightAla: point(noseBase.x + alaSpan, noseBase.y - 2),
    leftCheek,
    rightCheek,
    leftJaw,
    rightJaw,
    mouth,
    chin
  });
  return Object.freeze({
    frame: FRAME,
    faceScale: p.faceWidth / 100,
    anchors
  });
}

/** To compare face-local CSS centers to DOM rectangles in portrait space. */
export function toPortraitCoordinates(face, anchor) {
  return Object.freeze({
    x: FRAME.x + FRAME.centerX + (anchor.x - FRAME.centerX) * face.faceScale,
    y: FRAME.y + anchor.y
  });
}

/** One set of variables consumed by many CSS anatomical layers. */
export function deriveFaceStructureStyle(raw) {
  const a = deriveFaceGeometry(raw).anchors;
  const variables = {};
  for (const [name, anchor] of Object.entries(a)) {
    variables[`--fg-${name}-x`] = `${anchor.x.toFixed(2)}px`;
    variables[`--fg-${name}-y`] = `${anchor.y.toFixed(2)}px`;
  }
  return Object.freeze(variables);
}
