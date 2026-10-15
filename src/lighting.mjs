/** Single 3D-direction vector shared by plane, relief and stroke shading. */
import { lightVector } from './volume.mjs';

export const LIGHT_MODES = Object.freeze(['front', 'side', 'top', 'cinematic', 'custom']);
const lightClamp = (v, min, max) => Math.min(max, Math.max(min, v));
export function normalizeLighting(input = {}) {
  const source = input && typeof input === 'object' ? input : {};
  const mode = LIGHT_MODES.includes(source.mode) ? source.mode : 'cinematic';
  const direction = Number.isFinite(source.direction) ? lightClamp(source.direction, -60, 60) : -30;
  return { mode, direction };
}

export function deriveLightingRig(raw) {
  const setting = normalizeLighting(raw);
  const choices = {
    front: [0, 24],
    side: [53, 24],
    top: [0, 73],
    cinematic: [-38, 42],
    custom: [setting.direction, 24]
  };
  const [azimuth, elevation] = choices[setting.mode];
  const vector = lightVector(azimuth, elevation);
  const lightPosition = 50 + azimuth / 60 * 22;
  return Object.freeze({
    mode: setting.mode,
    azimuth, elevation, vector,
    css: Object.freeze({
      '--light-x': lightPosition.toFixed(2) + '%',
      '--shadow-x': (100 - lightPosition).toFixed(2) + '%',
      '--light-elevation': String(elevation)
    })
  });
}
