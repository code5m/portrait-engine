export const DEFINITIONS = Object.freeze({
  faceWidth: { min: 80, max: 120, step: 1, value: 100, group: 'geometry', unit: '%' },
  eyeSpacing: { min: -16, max: 16, step: 1, value: 0, group: 'geometry', unit: 'px' },
  noseWidth: { min: 80, max: 125, step: 1, value: 100, group: 'geometry', unit: '%' },
  jaw: { min: 82, max: 118, step: 1, value: 100, group: 'geometry', unit: '%' },
  graphite: { min: 15, max: 100, step: 1, value: 65, group: 'finish', unit: '%' },
  hatching: { min: 0, max: 100, step: 1, value: 62, group: 'finish', unit: '%' },
  hairVolume: { min: 75, max: 125, step: 1, value: 100, group: 'finish', unit: '%' }
});

export const PRESETS = Object.freeze({
  classic: { faceWidth: 100, eyeSpacing: 0, noseWidth: 100, jaw: 100, graphite: 65, hatching: 62, hairVolume: 100 },
  gentle: { faceWidth: 90, eyeSpacing: 6, noseWidth: 85, jaw: 88, graphite: 46, hatching: 43, hairVolume: 110 },
  angular: { faceWidth: 109, eyeSpacing: -4, noseWidth: 115, jaw: 115, graphite: 87, hatching: 86, hairVolume: 90 }
});

export const KEYS = Object.freeze(Object.keys(DEFINITIONS));
export function defaults() {
  return Object.fromEntries(KEYS.map(key => [key, DEFINITIONS[key].value]));
}
export function normalize(raw, fallback = defaults()) {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return { ...fallback };
  const output = {};
  for (const key of KEYS) {
    const config = DEFINITIONS[key];
    const value = raw[key];
    const parsed = typeof value === 'number' ? value : NaN;
    const prior = fallback[key];
    const safe = Number.isFinite(parsed) ? parsed : prior;
    output[key] = Math.max(config.min, Math.min(config.max, Math.round(safe / config.step) * config.step));
  }
  return output;
}
export function equal(a, b) { return KEYS.every(key => a[key] === b[key]); }
export function encode(data) { return JSON.stringify({ format: 'portrait-engine-params', version: 1, parameters: normalize(data) }, null, 2); }
export function decode(json) {
  const parsed = JSON.parse(json);
  if (parsed?.format !== 'portrait-engine-params' || parsed?.version !== 1 || !parsed.parameters || typeof parsed.parameters !== 'object') throw new Error('Unsupported portrait file');
  if (!KEYS.some(key => Number.isFinite(parsed.parameters[key]))) throw new Error('No valid parameters');
  return normalize(parsed.parameters);
}
