/** S5/S6 remain native CSS regions. No texture, canvas or per-mesh-face DOM. */
import {draw as drawStudy,edgeClipPath} from './study_renderer.mjs';
const names=new Set(['form-hatching','cross-hatching','graphite-granulation','scalp-mass','scalp-fibres']);
export function draw(target,descriptor,mode='tone') {
  if (!['S5','S6'].includes(descriptor.stage)) throw new TypeError('Unknown surface stage');
  if (!['tone','structure','masses','edges-control','material-control','hair-control'].includes(mode)) throw new TypeError('Unknown surface view');
  const layers=descriptor.surfaceRegions;
  if (!Array.isArray(layers)||layers.length!==5||new Set(layers.map(r=>r.name)).size!==5) throw new RangeError('Surface layer contract');
  let points=0;
  for (const r of layers) {
    if (!names.has(r.name)||!Array.isArray(r.rings)||!Number.isInteger(r.gray)||r.gray<0||r.gray>255||!Number.isFinite(r.opacity)||r.opacity<0||r.opacity>1) throw new TypeError('Unsafe surface layer');
    points+=r.rings.reduce((n,ring)=>n+ring.length,0);
  }
  if (points!==descriptor.surfaceContourPoints||points>60000) throw new RangeError('Surface contour budget');
  const baseMode=['material-control','hair-control'].includes(mode)?'tone':mode;
  drawStudy(target,{...descriptor,stage:'S4'},baseMode);
  if (['tone','hair-control'].includes(mode)) {
    for (const r of layers) {
      if (mode==='hair-control'&&r.name.startsWith('scalp-')) continue;
      const ink=document.createElement('i');ink.className='tone-region surface-region';ink.dataset.materialLayer=r.name;
      ink.style.clipPath=edgeClipPath(r.rings);ink.style.background=`rgb(${r.gray},${r.gray},${r.gray})`;ink.style.opacity=String(r.opacity);
      target.append(ink);
    }
  }
  target.dataset.mode=mode;target.dataset.stage=descriptor.stage;
}
