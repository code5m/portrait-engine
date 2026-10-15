import {clamp01} from '../face-dna.mjs';
export const EXPRESSION_PRESETS = Object.freeze({
neutral:{browRaise:.5,eyeTension:.2,mouthSmile:.5,jawOpen:0},
happy:{browRaise:.64,eyeTension:.42,mouthSmile:.9,jawOpen:.22},
sad:{browRaise:.35,eyeTension:.28,mouthSmile:.15,jawOpen:.08},
angry:{browRaise:.12,eyeTension:.86,mouthSmile:.28,jawOpen:.04},
fear:{browRaise:.88,eyeTension:.75,mouthSmile:.3,jawOpen:.68}
});
export function normalizeExpression(raw={}) {
 const v=typeof raw==='string'?EXPRESSION_PRESETS[raw]??EXPRESSION_PRESETS.neutral:raw;
 return Object.fromEntries(Object.entries(EXPRESSION_PRESETS.neutral).map(([k,x])=>[k,clamp01(v?.[k],x)]));
}
