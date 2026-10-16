/** S1: analytic form/light -> bounded CSS regions. No image or pixel inputs.
 * Geometry is in camera coordinates (+X right, +Y up, +Z viewer).
 * A/B/C change representation only. Ground bounce is a stated hemisphere
 * approximation, not a claim of a complete global-illumination solution.
 */
import {unit, srgb, surfacePoint, bandContour, sceneMarkup} from './sketch-s0.mjs';
export const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
export const add=(a,b)=>a.map((x,i)=>x+b[i]);
export const mul=(a,k)=>a.map(x=>x*k);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const tau=2*Math.PI, clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const linear=x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4;
const gray=x=>{const v=Math.round(255*srgb(x));return `rgb(${v},${v},${v})`;};
function positive(x,name){if(!Number.isFinite(x)||x<=0)throw new RangeError(name);}
export function validateShape(s){
 if(s.kind==='ellipsoid'){surfacePoint([0,0,1],s.radii);}
 else if(s.kind==='cylinder'){positive(s.radius,'radius');positive(s.halfHeight,'height');if(!Number.isFinite(s.tilt)||Math.abs(s.tilt)>=70)throw new RangeError('tilt');}
 else if(s.kind==='wedge'){if(!Array.isArray(s.half)||s.half.length!==3)throw new TypeError('half extents');s.half.forEach(x=>positive(x,'extent'));if(!Number.isFinite(s.yaw)||Math.abs(s.yaw)>=70)throw new RangeError('yaw');}
 else throw new RangeError('Unregistered primitive family');
 return s;
}
export function rotateX(p,degrees){const a=degrees*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return [p[0],c*p[1]-s*p[2],s*p[1]+c*p[2]];}
export function rotateY(p,degrees){const a=degrees*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return [c*p[0]+s*p[2],p[1],-s*p[0]+c*p[2]];}
export function wedgeFaces(s){
 const [x,y,z]=s.half;
 const v=[[-x,-y,-z],[x,-y,-z],[x,-y,z],[-x,-y,z],[-x,y,-z],[x,y,-z],[x,.15*y,z],[-x,.15*y,z]].map(p=>rotateY(p,s.yaw));
 const center=v.reduce((a,p)=>add(a,mul(p,1/8)),[0,0,0]);
 return [[0,3,2,1],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5],[4,5,6,7]].map(ids=>{
  let points=ids.map(i=>v[i]),normal=unit(cross(add(points[1],mul(points[0],-1)),add(points[2],mul(points[0],-1))));
  if(dot(normal,add(points[0],mul(center,-1)))<0){points=points.reverse();normal=mul(normal,-1);}
  return {points,normal};
 });
}
/** Exact support map. Shared by contact, silhouettes and cast shadows. */
export function support(s,direction){
 validateShape(s);const d=unit(direction);
 if(s.kind==='ellipsoid')return surfacePoint(d,s.radii);
 if(s.kind==='wedge')return wedgeFaces(s).flatMap(f=>f.points).reduce((best,p)=>dot(p,d)>dot(best,d)?p:best);
 const q=rotateX(d,-s.tilt),r=Math.hypot(q[0],q[2]);
 return rotateX([r>1e-12?s.radius*q[0]/r:0,q[1]>=0?s.halfHeight:-s.halfHeight,r>1e-12?s.radius*q[2]/r:0],s.tilt);
}
export function illumination(normal,light,config,bounce=false){
 const n=unit(normal),l=unit(light),g=unit(config.groundNormal);
 const gain=bounce?config.bounceStrength*config.receiverAlbedo*config.direct*Math.max(0,dot(g,l)):0;
 return {direct:config.direct*Math.max(0,dot(n,l)),bounce:gain*(1-dot(n,g))/2,ambient:config.ambient};
}
export function value(n,l,c,b=false){const r=illumination(n,l,c,b);return r.direct+r.bounce+r.ambient;}
/** Boundaries of spherical half-space intersections. Each boundary is an
 * analytic small-circle arc. Sample only these curves, never a screen grid.
 * Multiple loops are retained rather than convexifying a crescent or hole.
 */
export function capLoops(input,samples=160){
 if(!Number.isInteger(samples)||samples<24||samples>512)throw new RangeError('curve budget');
 const constraints=[];
 for(const [a,d] of input){
  if(!a.every(Number.isFinite)||!Number.isFinite(d))throw new TypeError('finite plane required');
  const len=Math.hypot(...a);
  if(len<1e-12){if(d>0)return [];continue;}
  const k=d/len;
  if(k>=1-1e-12)return [];
  if(k<=-1+1e-12)continue;
  const axis=mul(a,1/len);
  if(!constraints.some(c=>Math.abs(c[1]-k)<1e-10&&dot(c[0],axis)>1-1e-10))constraints.push([axis,k]);
 }
 const arcs=[];
 for(let i=0;i<constraints.length;i++){
  const [a,d]=constraints[i],u=unit(cross(a,Math.abs(a[2])>.9?[0,1,0]:[0,0,1])),v=cross(a,u),r=Math.sqrt(1-d*d);
  const at=t=>add(mul(a,d),mul(add(mul(u,Math.cos(t)),mul(v,Math.sin(t))),r));
  const cuts=[0,tau];
  for(let j=0;j<constraints.length;j++)if(j!==i){
   const [b,e]=constraints[j],B=r*dot(u,b),C=r*dot(v,b),R=Math.hypot(B,C),q=e-d*dot(a,b);
   if(R>1e-12&&Math.abs(q)<R-1e-12){
    const phase=Math.atan2(C,B),delta=Math.acos(clamp(q/R,-1,1));
    for(const t of [phase-delta,phase+delta])cuts.push((t%tau+tau)%tau);
   }
  }
  cuts.sort((x,y)=>x-y);
  const unique=cuts.filter((x,k)=>!k||x-cuts[k-1]>1e-9);
  for(let k=0;k<unique.length-1;k++){
   const lo=unique[k],hi=unique[k+1],mid=at((lo+hi)/2);
   if(!constraints.every(([b,e])=>dot(mid,b)>=e-1e-9))continue;
   const steps=Math.max(2,Math.ceil((hi-lo)/tau*samples));
   arcs.push(Array.from({length:steps+1},(_,j)=>at(lo+(hi-lo)*j/steps)));
  }
 }
 const loops=[];
 while(arcs.length){
  const loop=arcs.pop();let guard=0;
  while(Math.hypot(...add(loop[0],mul(loop.at(-1),-1)))>1e-6){
   const end=loop.at(-1),index=arcs.findIndex(a=>Math.hypot(...add(a[0],mul(end,-1)))<1e-6);
   if(index<0||guard++>64)throw new Error('Unclosed analytic contour');
   loop.push(...arcs.splice(index,1)[0].slice(1));
  }
  if(loop.length>3)loops.push(loop);
 }
 return loops;
}
function polygon(loops,project){
 const paths=loops.filter(p=>p.length>=3).map(loop=>loop.map(project));
 if(!paths.length)return 'polygon(0 0,0 0,0 0)';
 const anchor=paths[0][0],joined=[];
 for(const path of paths)joined.push(anchor,...path,path[0],anchor);
 return 'polygon(evenodd,'+joined.map(p=>p.map(x=>x.toFixed(4)+'%').join(' ')).join(',')+')';
}
function pixelProject(p,c){return [50+100*p[0]/c.orthoScale,50-100*p[1]/c.orthoScale];}
export function shadowGeometry(shape,light,c){
 const g=unit(c.groundNormal),l=unit(light),den=dot(g,l);
 if(den<=.08)throw new RangeError('Light must face receiving plane; grazing/backlight unsupported');
 const contact=support(shape,mul(g,-1)),offset=dot(g,contact);
 const points=Array.from({length:c.curveSamples},(_,i)=>{
  const a=tau*i/c.curveSamples,d=[Math.cos(a),Math.sin(a),0];
  const p=support(shape,add(d,mul(g,-dot(l,d)/den)));
  return add(p,mul(l,-(dot(g,p)-offset)/den));
 });
 return {normal:g,offset,contact,points};
}
export function ellipsoidToneLoops(shape,l,c,threshold,bounce){
 const light=unit(l),g=unit(c.groundNormal);
 const gain=bounce?c.bounceStrength*c.receiverAlbedo*c.direct*Math.max(0,dot(g,light)):0;
 const camera=[[0,0,1],0];
 if(!gain)return capLoops([camera,[light,(threshold-c.ambient)/c.direct]],c.curveSamples);
 // Union of two disjoint radiance branches. Ambient is not called bounce.
 const lit=capLoops([camera,[light,0],[add(mul(light,c.direct),mul(g,-gain/2)),threshold-c.ambient-gain/2]],c.curveSamples);
 const dark=capLoops([camera,[mul(light,-1),0],[mul(g,-gain/2),threshold-c.ambient-gain/2]],c.curveSamples);
 return [...lit,...dark];
}
function candidateEllipsoid(shape,light,c){
 // B16: deliberately test an elliptical radial approximation inside each
 // isophote band. It is not assumed correct just because it looks smoother.
 const w=2*shape.radii[0]/c.orthoScale*c.frameSize,h=2*shape.radii[1]/c.orthoScale*c.frameSize;
 let html=`<div class="form" style="width:${w}px;height:${h}px;background:${gray(c.ambient)}">`;
 for(let i=0;i<16;i++){
  const t=i/16,clip=bandContour(shape.radii,light.direction,t,c.curveSamples);
  const points=[...clip.matchAll(/([-\d.]+)% ([-\d.]+)%/g)].map(m=>[+m[1],+m[2]]);
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const rx=Math.max(.01,(maxX-minX)/2),ry=Math.max(.01,(maxY-minY)/2),cx=(maxX+minX)/2,cy=(maxY+minY)/2;
  const inner=100*Math.sqrt(Math.max(0,1-((i+1)/16)**2)/Math.max(1e-9,1-t*t));
  const low=gray(c.ambient+c.direct*t),high=gray(c.ambient+c.direct*(i+1)/16);
  html+=`<i style="clip-path:${clip};background:radial-gradient(ellipse ${rx}% ${ry}% at ${cx}% ${cy}%,${high} ${inner}%,${low} 100%)"></i>`;
 }
 return html+'</div>';
}
function primitiveMarkup(shape,light,c,variant,bounce){
 const levels=variant==='flat16'||variant==='gradient16'?16:32;
 if(shape.kind==='ellipsoid'&&(!bounce||c.receiverAlbedo*c.bounceStrength*c.direct<=1e-12)){
  return variant==='gradient16'?candidateEllipsoid(shape,light,c):sceneMarkup({...c,bands:levels},shape,light,levels);
 }
 let html='<div class="surface">';
 const patch=(points,color)=>`<i style="clip-path:${polygon([points],p=>pixelProject(p,c))};background:${color}"></i>`;
 if(shape.kind==='ellipsoid'){
  const g=unit(c.groundNormal),l=unit(light.direction),gain=c.bounceStrength*c.receiverAlbedo*c.direct*Math.max(0,dot(g,l));
  const w=2*shape.radii[0]/c.orthoScale*c.frameSize,h=2*shape.radii[1]/c.orthoScale*c.frameSize;
  html=`<div class="form" style="width:${w}px;height:${h}px;background:${gray(c.ambient)}">`;
  for(let i=0;i<levels;i++){
   const low=srgb(c.ambient),span=srgb(c.ambient+c.direct+gain)-low;
   const t=linear(low+span*i/levels);
   const loops=ellipsoidToneLoops(shape,l,c,t,bounce);
   const clip=polygon(loops,n=>{const p=surfacePoint(n,shape.radii);return [50+50*p[0]/shape.radii[0],50-50*p[1]/shape.radii[1]];});
   html+=`<i style="clip-path:${clip};background:${gray(linear(low+span*(i+.5)/levels))}"></i>`;
  }
 }else if(shape.kind==='wedge'){
  for(const f of wedgeFaces(shape))if(f.normal[2]>1e-8)html+=patch(f.points,gray(value(f.normal,light.direction,c,bounce)));
 }else{
  const point=(a,y)=>rotateX([shape.radius*Math.sin(a),y,shape.radius*Math.cos(a)],shape.tilt);
  const normal=a=>rotateX([Math.sin(a),0,Math.cos(a)],shape.tilt);
  // Nested angular superlevel regions prevent antialiased white seams.
  // The end-cap arcs are sampled as curves, not replaced with straight chords.
  const intervalPoints=(a,b)=>{
   const count=Math.max(3,Math.ceil((b-a)/Math.PI*c.curveSamples/2));
   const angles=Array.from({length:count+1},(_,j)=>a+(b-a)*j/count);
   return [...angles.map(t=>point(t,-shape.halfHeight)),...angles.reverse().map(t=>point(t,shape.halfHeight))];
  };
  html+=patch(intervalPoints(-Math.PI/2,Math.PI/2),gray(c.ambient));
  const l=unit(light.direction),g=unit(c.groundNormal),gain=bounce?c.bounceStrength*c.receiverAlbedo*c.direct*Math.max(0,dot(g,l)):0;
  const low=srgb(c.ambient),span=srgb(c.ambient+c.direct+gain)-low;
  const f=a=>value(normal(a),l,c,bounce);
  for(let i=1;i<levels-1;i++){
   const threshold=linear(low+span*(i-.5)/(levels-2)),color=gray(linear(low+span*i/(levels-2)));
   const cuts=[-Math.PI/2,Math.PI/2];
   for(let j=0;j<64;j++){
    let a=-Math.PI/2+Math.PI*j/64,b=-Math.PI/2+Math.PI*(j+1)/64;
    if((f(a)-threshold)*(f(b)-threshold)>=0)continue;
    const sign=f(a)>=threshold;
    for(let k=0;k<32;k++){const mid=(a+b)/2;if((f(mid)>=threshold)===sign)a=mid;else b=mid;}
    cuts.push((a+b)/2);
   }
   cuts.sort((a,b)=>a-b);
   const loops=[];
   for(let j=0;j<cuts.length-1;j++)if(f((cuts[j]+cuts[j+1])/2)>=threshold)loops.push(intervalPoints(cuts[j],cuts[j+1]));
   html+=`<i style="clip-path:${polygon(loops,p=>pixelProject(p,c))};background:${color}"></i>`;
  }
  const sign=shape.tilt>=0?1:-1;
  html+=patch(Array.from({length:c.curveSamples},(_,i)=>point(tau*i/c.curveSamples,sign*shape.halfHeight)),gray(value(rotateX([0,sign,0],shape.tilt),light.direction,c,bounce)));
 }
 return html+'</div>';
}
export function renderScene(shape,light,c,{variant='flat32',bounce=false,layer='form'}={}){
 validateShape(shape);unit(light.direction);unit(c.groundNormal);
 if(!Number.isInteger(c.curveSamples)||c.curveSamples<24||c.curveSamples>512)throw new RangeError('curve samples');
 if(!['flat16','gradient16','flat32'].includes(variant))throw new RangeError('variant');
 if(!['form','shadow','composite'].includes(layer))throw new RangeError('layer');
 for(const key of ['ambient','direct','receiverAlbedo','bounceStrength'])if(!Number.isFinite(c[key])||c[key]<0||c[key]>1)throw new RangeError(key);
 positive(c.frameSize,'frameSize');positive(c.orthoScale,'orthoScale');
 let html='';
 if(layer!=='form'){
  const shadow=shadowGeometry(shape,light.direction,c);
  const background=layer==='shadow'?'white':gray(c.receiverAlbedo*(c.ambient+c.direct*Math.max(0,dot(shadow.normal,unit(light.direction)))));
  html+=`<div class="receiver" style="background:${background}"></div><i class="cast-shadow" style="clip-path:${polygon([shadow.points],p=>pixelProject(p,c))};background:${layer==='shadow'?'black':gray(c.ambient*c.receiverAlbedo)}"></i>`;
 }
 if(layer!=='shadow')html+=primitiveMarkup(shape,light,c,variant,bounce);
 return html;
}
export function cases(c){return c.profiles.flatMap(shape=>(shape.split==='holdout'?c.holdoutLights:c.lights).map(light=>({id:shape.id+'-'+light.id,shape,light})));}
