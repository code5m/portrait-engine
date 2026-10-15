import {normalizeFaceDNA,legacyParametersFromDNA,dnaFromLegacyParameters,deriveIdentityFingerprint} from './face-dna.mjs';
import {deriveDNAGeometryStyle} from './face-geometry.mjs';
import {derivePortraitStyle} from './geometry.mjs';
import {deriveVolumeStyle} from './volume.mjs';
import {deriveSurfaceFieldStyle} from './surface-field.mjs';
import {deriveStrokeFieldStyle} from './stroke-field.mjs';
import {normalizeExpression} from './expression/expression-dna.mjs';
import {deriveExpressionStyle} from './expression/expression-engine.mjs';
import {normalizeHair} from './hair/hair-field.mjs';
import {deriveHairStyle} from './hair/hair-generator.mjs';
import {normalizeSkin,deriveSkinStyle} from './material/skin-material.mjs';
import {deriveArtisticSurfaceStyle} from './material/artistic-surface.mjs';
import {normalizeLighting,deriveLightingRig} from './lighting.mjs';
import {normalize,defaults} from './parameters.mjs';
export function buildFaceState(input={}) {
 const params=normalize(input.parameters??defaults());
 const faceDNA=normalizeFaceDNA(input.faceDNA??dnaFromLegacyParameters(params));
 const expression=normalizeExpression(input.expression);
 const hair=normalizeHair(input.hair);
 const skin=normalizeSkin(input.skin);
 const lighting=normalizeLighting(input.lighting??{mode:'custom',direction:params.lightDirection});
 return {id:typeof input.id==='string'?input.id:'custom',faceDNA,expression,hair,skin,lighting,parameters:legacyParametersFromDNA(faceDNA,params)};
}
export function deriveEngineStyle(input) {
 const state=buildFaceState(input);const rig=deriveLightingRig(state.lighting);
 const p={...state.parameters,lightDirection:rig.azimuth,lightElevation:rig.elevation};
 return Object.freeze({...derivePortraitStyle(p),...deriveDNAGeometryStyle(state.faceDNA),
 ...deriveVolumeStyle(p),...deriveSurfaceFieldStyle(p,state.faceDNA),
 ...deriveStrokeFieldStyle(p,state.faceDNA),...deriveExpressionStyle(state.expression),
 ...deriveHairStyle(state.hair),...deriveSkinStyle(state.skin),
 ...deriveArtisticSurfaceStyle({graphite:p.graphite/100,hatching:p.hatching/100}),...rig.css});
}
export function encodeFaceState(raw) {
 const state=buildFaceState(raw);
 return JSON.stringify({format:'portrait-engine-character',version:2,identity:{id:state.id,fingerprint:deriveIdentityFingerprint(state.faceDNA)},state},null,2);
}
export function decodeFaceState(serialized) {
 const json=JSON.parse(serialized);
 if(json?.format==='portrait-engine-params'&&json.version===1) {
  const p=normalize(json.parameters);return buildFaceState({parameters:p});
 }
 if(json?.format!=='portrait-engine-character'||json.version!==2||!json.state||typeof json.state!=='object')throw new Error('Unsupported character file');
 const state=buildFaceState(json.state);
 if(json.identity?.fingerprint!==deriveIdentityFingerprint(state.faceDNA))throw new Error('Identity fingerprint mismatch');
 return state;
}
