/** S0 instrument: geometry-derived CSS tone regions, not pixel drawing.
 * Reference space: right +X, up +Y, viewer +Z. Orthographic camera.
 * Only ellipsoids in this calibration. No human anatomy/realism claim.
 */
export function unit(v) {
  if (!Array.isArray(v) || v.length !== 3 || !v.every(Number.isFinite)) throw new TypeError('Expected finite 3-vector');
  const length = Math.hypot(...v);
  if (length < 1e-10) throw new RangeError('Zero direction');
  return v.map(x => x / length);
}
const dot = (a,b) => a.reduce((s,x,i) => s+x*b[i],0);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
export function srgb(linear) {
  if (!Number.isFinite(linear)) throw new TypeError('Nonfinite radiance');
  const x=Math.max(0,Math.min(1,linear));
  return x <= .0031308 ? 12.92*x : 1.055*Math.pow(x,1/2.4)-.055;
}
export function surfacePoint(normal,radii) {
  if (!Array.isArray(radii)||radii.length!==3||!radii.every(x=>Number.isFinite(x)&&x>0)) throw new RangeError('Positive ellipsoid radii required');
  const n=unit(normal), den=Math.hypot(...n.map((x,i)=>x*radii[i]));
  return n.map((x,i)=>x*radii[i]*radii[i]/den);
}
export function radiance(normal,light,ambient=.08,direct=.72) {
  return ambient + direct*Math.max(0,dot(unit(normal),unit(light)));
}
/** Project the boundary of N dot L >= threshold on the visible hemisphere.
 * Samples GEOMETRIC curves, not screen pixels. <= 17 DOM patches per form.
 */
export function bandContour(radii,light,threshold,samples=160) {
  if (!Number.isFinite(threshold)||threshold<0||threshold>=1) throw new RangeError('threshold in [0,1)');
  if (!Number.isInteger(samples)||samples<24||samples>512) throw new RangeError('bounded contour samples');
  const l=unit(light), axis=Math.abs(l[2])>.9?[0,1,0]:[0,0,1];
  const u=unit(cross(l,axis)), v=cross(l,u), radius=Math.sqrt(1-threshold*threshold), points=[];
  const add=n=>{
    const p=surfacePoint(n,radii);
    points.push([50+50*p[0]/radii[0],50-50*p[1]/radii[1]]);
  };
  for(let i=0;i<samples;i++) {
    const a=2*Math.PI*i/samples, c=Math.cos(a),s=Math.sin(a);
    const n=l.map((x,j)=>threshold*x+radius*(u[j]*c+v[j]*s));
    if(n[2]>=-1e-9)add(n);
    const edge=[c,s,0];
    if(dot(edge,l)>=threshold-1e-9)add(edge);
  }
  if(points.length<3)return 'polygon(0 0,0 0,0 0)';
  const center=points.reduce((p,q)=>[p[0]+q[0]/points.length,p[1]+q[1]/points.length],[0,0]);
  points.sort((a,b)=>Math.atan2(a[1]-center[1],a[0]-center[0])-Math.atan2(b[1]-center[1],b[0]-center[0]));
  return 'polygon('+points.map(p=>p.map(x=>x.toFixed(3)+'%').join(' ')).join(',')+')';
}
export function sceneMarkup(config,profile,light,levels=config.bands) {
  if(!Number.isInteger(levels)||levels<2||levels>32)throw new RangeError('2..32 bands');
  const width=2*profile.radii[0]/config.orthoScale*config.frameSize;
  const height=2*profile.radii[1]/config.orthoScale*config.frameSize;
  const gray=x=>Math.round(255*srgb(x));
  const patches=Array.from({length:levels},(_,i)=>{
    const color=gray(config.ambient+config.direct*(i+.5)/levels);
    return '<i style="clip-path:'+bandContour(profile.radii,light.direction,i/levels,config.curveSamples)+';background:rgb('+color+','+color+','+color+')"></i>';
  }).join('');
  const base=gray(config.ambient);
  return '<div class="form" style="width:'+width+'px;height:'+height+'px;background:rgb('+base+','+base+','+base+')">'+patches+'</div>';
}
if(typeof document!=='undefined') {
  // Shared numerical fixture is embedded by the offline builder, never a bitmap.
  const config=JSON.parse(document.getElementById('scene-config').textContent);
  const params=new URLSearchParams(location.search),selection=params.get('scene');
  const levels=params.get('levels')==='3'?3:config.bands;
  if(selection)document.body.classList.add('single-scene');
  const grid=document.getElementById('grid');
  for(const profile of config.profiles) for(const light of config.lights) {
    const id=profile.id+'-'+light.id;
    if(selection&&selection!==id)continue;
    const card=document.createElement('section');
    card.className='card';
    const title=document.createElement('h2');title.textContent=profile.id+' / '+light.id;
    const scene=document.createElement('div');scene.className='scene';scene.dataset.scene=id;
    scene.innerHTML=sceneMarkup(config,profile,light,levels);
    card.append(title,scene);grid.append(card);
  }
  document.documentElement.dataset.ready='true';
}
