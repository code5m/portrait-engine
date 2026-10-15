import {clamp01} from '../face-dna.mjs';
export function deriveArtisticSurfaceStyle(raw={}) {
 return Object.freeze({
 '--art-graphite':clamp01(raw?.graphite,.65).toFixed(3),
 '--art-paper':clamp01(raw?.paper,.7).toFixed(3),
 '--art-hatching':clamp01(raw?.hatching,.62).toFixed(3)
 });
}
