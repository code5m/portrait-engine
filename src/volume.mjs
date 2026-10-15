/**
 * Research 006: a tiny, explicit 2.5D value model for CSS portrait studies.
 *
 * We deliberately approximate a face with stable FRONT-FACING plane normals.
 * There is no hidden bitmap, 3D mesh, canvas, WebGL or AI image. JavaScript
 * computes only numeric CSS custom properties; the browser draws everything.
 * Positive lightDirection lights the viewer-right side of the face.
 * These normals are artistic abstractions, NOT anthropometric measurements.
 */
import { normalize } from './parameters.mjs';

export const PLANE_NORMALS = Object.freeze({
  browLeft: Object.freeze([-0.38, 0.31, 0.87]),
  browRight: Object.freeze([0.38, 0.31, 0.87]),
  orbitLeft: Object.freeze([-0.53, -0.10, 0.69]),
  orbitRight: Object.freeze([0.53, -0.10, 0.69]),
  cheekLeft: Object.freeze([-0.67, -0.13, 0.72]),
  cheekRight: Object.freeze([0.67, -0.13, 0.72]),
  noseLeft: Object.freeze([-0.79, -0.08, 0.58]),
  noseRight: Object.freeze([0.79, -0.08, 0.58]),
  jawLeft: Object.freeze([-0.58, -0.58, 0.60]),
  jawRight: Object.freeze([0.58, -0.58, 0.60]),
  forehead: Object.freeze([0, 0.40, 0.92]),
  chin: Object.freeze([0, -0.53, 0.85])
});

const clamp=(x,min=0,max=1)=>Math.min(max,Math.max(min,x));
function dot(a,b){return a.reduce((v,x,i)=>v+x*b[i],0);}
function unit(v){const length=Math.hypot(...v);return v.map(x=>x/length);}

/**
 * One shared light in viewer coordinates. Elevation fixed at 24deg.
 * The additive 15% ambient term avoids pure-black holes in eye sockets.
 */
export function lightVector(degrees, elevationDegrees = 24){
  const safeDegrees = Number.isFinite(degrees) ? clamp(degrees,-60,60) : 0;
  const a=safeDegrees*Math.PI/180;
  const elev=clamp(elevationDegrees, 0, 85)*Math.PI/180;
  return Object.freeze([Math.sin(a)*Math.cos(elev),Math.sin(elev),Math.cos(a)*Math.cos(elev)]);
}

/** Values only. Artists may later replace the normals without reworking UI. */
export function deriveVolumeValues(raw){
  const p=normalize(raw);
  const light=lightVector(p.lightDirection, Number.isFinite(raw?.lightElevation) ? raw.lightElevation : 24);
  const planes={};
  for(const [name,n] of Object.entries(PLANE_NORMALS)){
    const normal=unit(n);
    const diffuse=clamp(dot(normal,light));
    // Contrast physically inspired, not physical cast shadows.
    const shade=clamp((1-(0.15+0.85*diffuse))*(0.22+0.78*(p.graphite/100)));
    const lightness=clamp(Math.pow(diffuse,2.8)*(0.2+0.12*(1-p.graphite/100)));
    planes[name]=Object.freeze({diffuse,shade,lightness});
  }
  return Object.freeze(planes);
}

/** DOM-independent style contract, anchored to the same face as geometry.mjs. */
export function deriveVolumeStyle(raw){
  const planes=deriveVolumeValues(raw);
  const p=normalize(raw);
  const styles={};
  for(const [name,value] of Object.entries(planes)){
    styles[`--v-${name}-shade`]=value.shade.toFixed(4);
    styles[`--v-${name}-light`]=value.lightness.toFixed(4);
  }
  styles['--v-hatch-strength']=(p.hatching/100).toFixed(4);
  styles['--v-cheek-x'] = `${(p.jaw-100)*0.14}px`;
  return Object.freeze(styles);
}
