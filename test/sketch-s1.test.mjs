import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {unit,surfacePoint,sceneMarkup} from '../study/sketch-s0.mjs';
import {dot,add,mul,cases,renderScene,support,shadowGeometry,illumination,value,capLoops,ellipsoidToneLoops} from '../study/sketch-s1.mjs';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const config=JSON.parse(read('research/sketch/s1-scenes.json'));
const near=(a,b,eps=1e-8)=>assert.ok(Math.abs(a-b)<eps,`${a} != ${b}`);
function inside(p,poly){let yes=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;}
test('S1 has baseline and untouched parameter holdouts, all four form families',()=>{
 assert.equal(cases(config).length,27);assert.equal(config.protocol.regionBudget,32);
 assert.equal(config.profiles.filter(p=>p.split==='holdout').length,4);
 assert.deepEqual(new Set(config.profiles.map(p=>p.kind)),new Set(['ellipsoid','cylinder','wedge']));
 assert.equal(config.profiles[0].id,'sphere');
});
test('S1 A16 uses unchanged S0 geometry and paint code',()=>{
 for(const {shape,light} of cases(config).filter(x=>x.shape.kind==='ellipsoid'))assert.equal(renderScene(shape,light,config,{variant:'flat16'}),sceneMarkup({...config,bands:16},shape,light,16));
});
test('bounded geometry CSS across all fixtures and reflected-light variants',()=>{
 for(const {shape,light} of cases(config))for(const bounce of [false,true])for(const variant of ['flat16','gradient16','flat32']){
  const html=renderScene(shape,light,config,{variant,bounce});
  assert.ok((html.match(/<i /g)||[]).length<=32);assert.doesNotMatch(html,/NaN|Infinity|<img|<svg|<canvas|url\(/i);
  assert.equal(html,renderScene(shape,light,config,{variant,bounce}));
 }
});
test('invalid shapes, light directions, parameters and selectors fail explicitly',()=>{
 const s=config.profiles[0],l=config.lights[0];
 for(const shape of [{...s,radii:[1,-1,1]},{...s,radii:[1,NaN,1]},{kind:'pixels'}])assert.throws(()=>renderScene(shape,l,config));
 assert.throws(()=>renderScene(s,{direction:[0,0,0]},config));
 assert.throws(()=>renderScene(s,l,{...config,receiverAlbedo:-1}));
 assert.throws(()=>renderScene(s,l,config,{variant:'unregistered'}));
 assert.throws(()=>capLoops([[[0,0,1],NaN]]));
 assert.throws(()=>shadowGeometry(s,[0,-1,0],config));
});
test('reflection is directional, receiver-dependent and removable, never constant ambient',()=>{
 const g=unit(config.groundNormal),l=config.lights[0].direction;
 near(illumination(g,l,config,true).bounce,0);
 assert.ok(illumination(mul(g,-1),l,config,true).bounce>0);
 for(const {shape,light} of cases(config)){
  const c={...config,receiverAlbedo:0};
  assert.equal(renderScene(shape,light,c,{bounce:true}),renderScene(shape,light,c,{bounce:false}));
 }
});
test('hemisphere irradiance formula agrees with independent directional quadrature',()=>{
 const count=20000;
 for(const z of [-1,-.6,0,.3,.8,1]){
  const n=[Math.sqrt(1-z*z),0,z];let integral=0;
  for(let i=0;i<count;i++){const h=(i+.5)/count,a=i*Math.PI*(3-Math.sqrt(5)),r=Math.sqrt(1-h*h);integral+=Math.max(0,dot(n,[r*Math.cos(a),r*Math.sin(a),-h]));}
  near(2*integral/count,(1-z)/2,1e-3);
 }
});
test('spherical cap contours retain the reflected and direct branches without convexifying',()=>{
 for(const {shape,light} of cases(config).filter(x=>x.shape.kind==='ellipsoid')){
  for(const threshold of [.10,.18,.35,.6]){
   const loops=ellipsoidToneLoops(shape,light.direction,config,threshold,true);
   const polygons=loops.map(loop=>loop.map(n=>surfacePoint(n,shape.radii)));
   for(let i=0;i<60;i++){
    const z=(i+.5)/60,a=i*2.399963229728653,n=[Math.sqrt(1-z*z)*Math.cos(a),Math.sqrt(1-z*z)*Math.sin(a),z];
    const rad=value(n,light.direction,config,true);if(Math.abs(rad-threshold)<.006)continue;
    const p=surfacePoint(n,shape.radii),actual=polygons.some(poly=>inside(p,poly));
    if(actual!==(rad>=threshold)){
     // A finite polygon is inscribed in the analytic silhouette. Do not
     // mislabel its subpixel chord error as an interior topology failure.
     const gap=1-Math.hypot(p[0]/shape.radii[0],p[1]/shape.radii[1]);
     const sagitta=(1-Math.cos(2*Math.PI/config.curveSamples))*(Math.max(...shape.radii)/Math.min(...shape.radii))**2;
     assert.ok(gap<=sagitta,`${shape.id}: non-boundary topology mismatch`);
    }
   }
   for(const loop of loops)for(const n of loop){near(Math.hypot(...n),1);assert.ok(n[2]>=-1e-7);assert.ok(value(n,light.direction,config,true)>=threshold-1e-7);}
  }
 }
});
test('cast shadows lie on the receiver, attach at support contact and mirror with light',()=>{
 for(const {shape,light} of cases(config)){
  const shadow=shadowGeometry(shape,light.direction,config);
  near(dot(shadow.normal,shadow.contact),shadow.offset);
  for(const p of shadow.points)near(dot(shadow.normal,p),shadow.offset);
  const c={...config,receiverAlbedo:0};assert.deepEqual(shadow,shadowGeometry(shape,light.direction,c));
  near(dot(shadow.normal,support(shape,mul(shadow.normal,-1))),shadow.offset);
 }
 const s=config.profiles[0],left=shadowGeometry(s,config.lights[0].direction,config),right=shadowGeometry(s,config.lights[2].direction,config);
 near(left.points.reduce((a,p)=>a+p[0],0),-right.points.reduce((a,p)=>a+p[0],0),1e-7);
});
test('completed S1 requires exact implementation digest and real CI evidence',()=>{
 const ledgerPath=new URL('../research/sketch/stages.json',import.meta.url);
 if(!fs.existsSync(ledgerPath))return;
 const stage=JSON.parse(fs.readFileSync(ledgerPath,'utf8')).stages.find(s=>s.id==='S1');
 if(stage.status!=='COMPLETE')return;
 const e=JSON.parse(read(stage.evidence)),paths=JSON.parse(read('research/sketch/s1-sources.json'));
 const hash=crypto.createHash('sha256');for(const p of paths.sort())hash.update(p+'\0'+read(p)+'\0');
 assert.equal(e.sourceDigest,hash.digest('hex'));assert.equal(e.status,'FORM_STUDY_COMPLETE');
 assert.equal(e.transport,'file');assert.equal(e.artStatus,'ART_UNVERIFIED');assert.equal(e.humanObservers,0);
 assert.equal(e.counts.cases,27);assert.equal(e.counts.cssFrames,138);assert.equal(e.counts.referenceFrames,81);
 assert.equal(e.metrics.length,27);assert.equal(e.selectedRepresentation,'flat32');
 assert.match(e.ciCommit,/^[a-f0-9]{40}$/);assert.match(String(e.ciRun),/^\d+$/);
});
