import {clamp01} from '../face-dna.mjs';
export function normalizeHair(raw={}) {
 return {density:clamp01(raw?.density,.6),length:clamp01(raw?.length,.6),curl:clamp01(raw?.curl,.25),direction:clamp01(raw?.direction,.5)};
}
export function sampleHairField(raw, count=24) {
 const h=normalizeHair(raw); const n=Math.min(128,Math.max(1,Math.floor(count)));
 return Object.freeze(Array.from({length:n},(_,i)=>{
 const t=(i+.5)/n, angle=(t-.5)*Math.PI+((h.direction-.5)*.7);
 return Object.freeze({rootX:Number((50+46*Math.sin(angle)).toFixed(2)),rootY:Number((19+16*Math.cos(angle)).toFixed(2)),angle:Number(angle.toFixed(4)),length:Number((38+120*h.length*(.7+.3*Math.sin(i*2.39996)**2)).toFixed(2)),weight:Number((.4+2.3*h.density).toFixed(2)),curl:h.curl});
 }));
}
