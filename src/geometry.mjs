import { normalize } from './parameters.mjs';

/**
 * Maps human-readable sliders into coordinated CSS landmarks.
 * The face is centered at x=190.5px in a fixed 380px drawing coordinate space.
 * A change to face width must also relocate both ears and widen the hair mass.
 * Lighting is deliberately a *stylized* 2D value model, not a physically
 * correct cast-shadow solver.
 */
export function derivePortraitStyle(raw) {
  const p = normalize(raw);
  const faceScale = p.faceWidth / 100;
  const halfDelta = 103.5 * (faceScale - 1);
  const light01 = (p.lightDirection + 60) / 120;
  const ink = p.graphite / 100;
  const shadowLeft = (0.19 + 0.66 * light01) * ink;
  const shadowRight = (0.19 + 0.66 * (1 - light01)) * ink;
  // Landmarks in the unscaled 380 x 500 CSS portrait coordinate system.
  // These are a deliberate drawing reference, not a claim of medical anatomy.
  const landmarks = deriveHeadLandmarks(p);
  return Object.freeze({
    '--face-x': String(faceScale),
    '--face-half-delta': `${halfDelta.toFixed(2)}px`,
    '--ear-shift': `${landmarks.earShift.toFixed(2)}px`,
    '--hair-structure-x': String(Number(((p.hairVolume / 100) * (1 + .78 * (faceScale - 1))).toFixed(4))),
    '--hair-x': String(Number(((p.hairVolume / 100) * (1 + .78 * (faceScale - 1))).toFixed(4))),
    '--eye-offset': `${p.eyeSpacing}px`,
    '--nose-x': String(p.noseWidth / 100),
    '--mouth-x': String(p.mouthWidth / 100),
    '--jaw-radius-left': `${50 - (p.jaw - 100) * .45}%`,
    '--jaw-radius-right': `${48 - (p.jaw - 100) * .45}%`,
    '--ink': String(ink),
    '--hatch': String(p.hatching / 100),
    '--light-x': `${(28 + 44 * light01).toFixed(1)}%`,
    '--shadow-x': `${(72 - 44 * light01).toFixed(1)}%`,
    '--shadow-left-opacity': shadowLeft.toFixed(4),
    '--shadow-right-opacity': shadowRight.toFixed(4),
    '--plane-shade-left': shadowLeft.toFixed(4),
    '--plane-shade-right': shadowRight.toFixed(4),
    '--key-light': light01.toFixed(4),
    '--face-cheek-scale': (1 + (p.jaw - 100) * .004).toFixed(4),
    '--nose-cast-x': `${(5 - 10 * light01).toFixed(1)}px`,
    '--forehead-shift': `${(-8 + 16 * light01).toFixed(1)}px`
  });
}

/**
 * Reference coordinates for styling and geometry regression checks.
 * Pure numerical landmarks: no DOM, image, canvas, or rendering side effects.
 */
function faceScale(p) { return p.faceWidth / 100; }

export function deriveHeadLandmarks(raw) {
  const p = normalize(raw);
  const centerX = 190.5;
  const halfWidth = (207 * p.faceWidth / 100) / 2;
  const eyeDelta = p.eyeSpacing;
  // Research 003: slightly different eye insets are intentional.  The
  // CSS eye groups are 57px wide, inset 29px (left) and 30px (right).
  // Avoid claiming perfect bilateral symmetry for an asymmetrical drawing.
  const leftHalfGap = (46 + eyeDelta) * faceScale(p);
  const rightHalfGap = (45 + eyeDelta) * faceScale(p);
  const leftEye = centerX - leftHalfGap;
  const rightEye = centerX + rightHalfGap;
  const earShift = 103.5 * (p.faceWidth / 100 - 1);
  return Object.freeze({
    centerX,
    faceLeft: centerX - halfWidth,
    faceRight: centerX + halfWidth,
    faceWidth: halfWidth * 2,
    leftEye,
    rightEye,
    eyeSpacing: rightEye - leftEye,
    leftEar: 89 - earShift,
    rightEar: 294 + earShift,
    earShift,
    browY: 214,
    eyeY: 249.5,
    noseBaseY: 333,
    mouthY: 373,
    chinY: 395,
  });
}
