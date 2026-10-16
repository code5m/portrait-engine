/** Numerical vector regions -> native CSS. Never renders a bitmap, mesh face,
 * canvas, SVG or WebGL. Reference images belong outside this drawing subtree. */
export function clipPath(rings) {
  if (!Array.isArray(rings)) throw new TypeError('Invalid rings');
  const paths = rings.filter(r=>Array.isArray(r)&&r.length>=3);
  if (!paths.length) return 'polygon(0 0,0 0,0 0)';
  const anchor=paths[0][0],points=[];
  for(const path of paths) {
    points.push(anchor,...path,path[0],anchor);
  }
  for(const p of points)if(!Array.isArray(p)||p.length!==2||!p.every(v=>Number.isFinite(v)&&v>=-50&&v<=150)) throw new RangeError('Unsafe contour');
  return 'polygon(evenodd,'+points.map(p=>p.map(v=>v.toFixed(5)+'%').join(' ')).join(',')+')';
}
export function draw(target,descriptor,mode='tone') {
  if(!['tone','structure'].includes(mode)||descriptor.renderer!=='HTML_CSS_REGIONS')throw new TypeError('Unknown renderer');
  const regions=mode==='tone'?descriptor.toneRegions:descriptor.structureRegions;
  if(!Array.isArray(regions)||regions.length>32||descriptor.contourPoints>60000)throw new RangeError('Region budget');
  const fragment=document.createDocumentFragment();
  for(const region of regions) {
    if(!Number.isInteger(region.gray)||region.gray<0||region.gray>255)throw new TypeError('Invalid gray');
    const el=document.createElement('i');el.className='tone-region';
    el.style.clipPath=clipPath(region.rings);el.style.background=`rgb(${region.gray},${region.gray},${region.gray})`;
    if(region.name)el.dataset.region=region.name;
    fragment.append(el);
  }
  target.replaceChildren(fragment);target.dataset.geometryHash=descriptor.geometry.geometryHash;
  target.dataset.contentHash=descriptor.contentHash;target.dataset.mode=mode;
}
