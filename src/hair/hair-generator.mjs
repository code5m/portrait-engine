import {normalizeHair,sampleHairField} from './hair-field.mjs';
export function deriveHairStyle(raw) {
 const h=normalizeHair(raw); const field=sampleHairField(h);
 return Object.freeze({
 '--hair-field-density':h.density.toFixed(3),
 '--hair-field-length':(0.8+h.length*.5).toFixed(3),
 '--hair-field-curl':(h.curl*19).toFixed(2)+'deg',
 '--hair-field-direction':((h.direction-.5)*24).toFixed(2)+'deg',
 '--hair-field-strands':String(field.length),
 '--hair-strand-pitch':(3.4+(1-h.density)*6).toFixed(2)+'px'
 });
}
