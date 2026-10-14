/**
 * Research 009 / Surface-bound graphite strokes, NOT a true drawing engine.
 * Same 12 relief-derived normals and one directional light as Research 008.
 * Numeric values only: actual marks are CSS repeating-gradients and masks.
 * The field is a small artistic study, not measured human anatomy.
 */
import { normalize } from './parameters.mjs';
import { deriveSurfaceField } from './surface-field.mjs';

export const STROKE_REGIONS = Object.freeze([
  'browLeft','browRight','orbitLeft','orbitRight',
  'noseLeft','noseRight','cheekLeft','cheekRight',
  'jawLeft','jawRight','chin'
]);
const clampStroke = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Gradient axis follows surface height derivative; hatch lines are its isoheight tangent. */
export function deriveStrokeField(raw) {
  const p = normalize(raw);
  const field = deriveSurfaceField(p);
  const patches = {};
  for (const name of STROKE_REGIONS) {
    const { normal, shade } = field.values[name];
    // atan2(x, -y) uses CSS gradient coordinates (0deg is up, 90deg right).
    // The positive/negative half-turn paints identical physical stroke axes.
    const radians = Math.atan2(-normal[0], normal[1]);
    let angle = radians * (180 / Math.PI);
    if (!Number.isFinite(angle)) angle = 0;
    angle = ((angle + 180) % 180 + 180) % 180;
    // Paper remains visible even at maximal pencil density; lit areas remain quiet.
    const opacity = clampStroke((shade - 0.16) * 0.68, 0, 0.39) * p.hatching / 100;
    patches[name] = Object.freeze({
      angle: Number(angle.toFixed(2)),
      opacity: Number(opacity.toFixed(4)),
      shade: Number(shade.toFixed(4))
    });
  }
  return Object.freeze(patches);
}

/** Names deliberately match face-local DOM region classes in study009.css. */
export function deriveStrokeFieldStyle(raw) {
  const field = deriveStrokeField(raw);
  const variables = {};
  for (const [name, {angle, opacity}] of Object.entries(field)) {
    variables[`--r009-${name}-angle`] = `${angle.toFixed(2)}deg`;
    variables[`--r009-${name}-opacity`] = opacity.toFixed(4);
  }
  return Object.freeze(variables);
}
