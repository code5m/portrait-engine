import { normalizeFaceDNA, deriveIdentityFingerprint } from '../face-dna.mjs';
export function createIdentity(raw) {
  if (!raw || typeof raw !== 'object' || !/^[a-z][a-z0-9-]{1,39}$/.test(raw.id)) throw new TypeError('Invalid identity id');
  const faceDNA = normalizeFaceDNA(raw.faceDNA);
  return Object.freeze({id:raw.id, name:String(raw.name || raw.id).slice(0,80), age:Math.min(120,Math.max(0,Number.isFinite(raw.age)?raw.age:35)), faceDNA, fingerprint:deriveIdentityFingerprint(faceDNA)});
}
