import {normalizeExpression} from './expression-dna.mjs';
export function deriveExpressionStyle(raw) {
 const e=normalizeExpression(raw);
 return Object.freeze({
 '--expr-brow-shift':((.5-e.browRaise)*10).toFixed(2)+'px',
 '--expr-brow-tilt':((e.eyeTension-.2)*-8).toFixed(2)+'deg',
 '--expr-eye-squint':(1-e.eyeTension*.3).toFixed(3),
 '--expr-mouth-curve':((e.mouthSmile-.5)*9).toFixed(2)+'px',
 '--expr-mouth-open':(1+e.jawOpen*.7).toFixed(3),
 '--expr-mouth-corner':((e.mouthSmile-.5)*14).toFixed(2)+'deg'
 });
}
