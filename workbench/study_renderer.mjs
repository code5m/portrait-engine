/** S3/S4 use the immutable CSS polygon painter; only S4 edge ribbons feather.
 * This module never imports a reference image or performs pixel rendering. */
import {draw as drawBase, clipPath} from './renderer.mjs';
export function draw(target, descriptor, mode='tone', edgeMode='selected') {
  if (!['S2','S3','S4'].includes(descriptor.stage)) throw new TypeError('Unregistered stage');
  if (!['selected','all','none'].includes(edgeMode)) throw new TypeError('Unregistered edge arm');
  target.style.clipPath='';
  if (mode==='masses') {
    if (!Array.isArray(descriptor.massRegions)||descriptor.massRegions.length!==3) throw new TypeError('Missing registered three-tone view');
    drawBase(target,{...descriptor,toneRegions:descriptor.massRegions},'tone');
    target.dataset.mode='masses';return;
  }
  if (mode==='edges-control') {
    if (descriptor.stage!=='S4') throw new TypeError('Control belongs to S4');
    mode='tone';edgeMode='all';
  }
  drawBase(target,descriptor,mode);
  if (descriptor.stage!=='S4' || mode!=='tone' || edgeMode==='none') return;
  const layers=edgeMode==='all'?descriptor.controlEdgeRegions:descriptor.edgeRegions;
  if (!Array.isArray(layers)||layers.length>3||descriptor.edgeContourPoints>32000) throw new RangeError('Edge budget');
  for (const region of layers) {
    if (!Number.isInteger(region.gray)||region.gray<0||region.gray>255 ||
        !Number.isFinite(region.opacity)||region.opacity<0||region.opacity>1 ||
        !Number.isFinite(region.blurPixels)||region.blurPixels<0||region.blurPixels>.5) throw new RangeError('Unsafe ink');
    const wrapper=document.createElement('span'); wrapper.className='edge-ribbon';
    wrapper.style.cssText='position:absolute;inset:0;display:block;pointer-events:none';
    // Clip only this ink layer. Clipping target would anti-alias the entire
    // already-painted S3 face again, changing pixels unrelated to edges.
    wrapper.style.clipPath=clipPath(descriptor.silhouetteRings);
    if (region.blurPixels)wrapper.style.filter=`blur(${region.blurPixels}px)`;
    wrapper.style.opacity=String(region.opacity);
    const ink=document.createElement('i');ink.className='tone-region';
    ink.style.clipPath=clipPath(region.rings);ink.style.background=`rgb(${region.gray},${region.gray},${region.gray})`;
    wrapper.append(ink);target.append(wrapper);
  }
  target.dataset.edgeMode=edgeMode;
}
