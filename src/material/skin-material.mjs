import {clamp01} from '../face-dna.mjs';
export function normalizeSkin(raw={}) {
 return {tone:clamp01(raw?.tone,.52),roughness:clamp01(raw?.roughness,.65),pore:clamp01(raw?.pore,.34)};
}
export function deriveSkinStyle(raw) {
 const skin=normalizeSkin(raw);
 return Object.freeze({
 '--skin-tone':(87-skin.tone*25).toFixed(2)+'%',
 '--skin-grain-opacity':(skin.pore*.22).toFixed(3),
 '--skin-softness':(1.6+skin.roughness*4).toFixed(2)+'px'
 });
}
