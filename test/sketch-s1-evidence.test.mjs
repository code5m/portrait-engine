/** Archive audit, separate from the measured S1 implementation.
 * Synthetic mutations here test rejection only; they never become study data.
 * This validates recorded evidence, NOT observer identity or portrait realism.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const config=read('research/sketch/s1-scenes.json');
const evidence=read('research/sketch/evidence/S1.json');
const protocol=config.protocol;
const expected=new Map(config.profiles.flatMap(shape =>
  (shape.split==='holdout'?config.holdoutLights:config.lights)
    .map(light=>[shape.id+'-'+light.id,{kind:shape.kind,split:shape.split}])));
function validate(e){
 assert.equal(e.schemaVersion,1);assert.equal(e.stage,'S1');
 assert.equal(e.status,'FORM_STUDY_COMPLETE');assert.equal(e.transport,'file');
 assert.equal(e.artStatus,'ART_UNVERIFIED');assert.equal(e.humanObservers,0);
 assert.deepEqual(e.failures,[]);
 for(const key of ['ciCommit','sourceHeadCommit'])assert.match(e[key],/^[a-f0-9]{40}$/);
 for(const key of ['sourceDigest','offlinePageSha256'])assert.match(e[key],/^[a-f0-9]{64}$/);
 assert.match(String(e.ciRun),/^\d+$/);
 assert.equal(e.counts.cases,expected.size);
 const cssCount=[...expected.values()].reduce((n,c)=>n+(c.kind==='ellipsoid'?6:4),0);
 assert.equal(e.counts.cssFrames,cssCount);assert.equal(e.counts.referenceFrames,expected.size*3);
 for(const split of ['baseline','holdout'])assert.equal(e.counts[split+'Cases'],[...expected.values()].filter(x=>x.split===split).length);
 assert.equal(e.metrics.length,expected.size);const seen=new Set();
 const upper={cssVsAnalyticMAE:protocol.selectedInteriorMAE,fullMAE:protocol.selectedFullMAE,
  edgeMAE:protocol.selectedEdgeMAE,referenceVsAnalyticMAE:protocol.referenceInteriorMAE,
  cssVsBlenderMAE:protocol.selectedInteriorMAE,compositeMAE:protocol.selectedFullMAE,
  shadowCentroidPixels:protocol.shadowCentroidPixels};
 for(const row of e.metrics){
  assert.ok(expected.has(row.scene)&&!seen.has(row.scene),'unknown/duplicate scene');seen.add(row.scene);
  assert.equal(row.kind,expected.get(row.scene).kind);assert.equal(row.split,expected.get(row.scene).split);
  for(const [key,limit] of Object.entries(upper)){
   assert.ok(Number.isFinite(row[key])&&row[key]>=0&&row[key]<limit,row.scene+' '+key+' violates protocol');
  }
  for(const key of ['shadowIoU','analyticShadowIoU'])assert.ok(Number.isFinite(row[key])&&row[key]>=protocol.shadowIoU&&row[key]<=1,row.scene+' '+key);
  assert.ok(Number.isFinite(row.bounceMeanDelta)&&row.bounceMeanDelta>.5,row.scene+' bounce response');
 }
 assert.equal(e.comparisons.length,6);const groups=new Map();
 for(const row of e.comparisons){
  const key=row.split+'/'+row.variant;
  assert.ok(['baseline','holdout'].includes(row.split));
  assert.ok(['flat16','gradient16','flat32'].includes(row.variant));
  assert.ok(!groups.has(key),'duplicate A/B/C comparison');groups.set(key,row);
  for(const field of ['interiorMAE','fullMAE','edgeMAE','gradientError'])assert.ok(Number.isFinite(row[field])&&row[field]>=0,field);
 }
 let gradient=true;
 for(const split of ['baseline','holdout']){
  const [a,b,c]=['flat16','gradient16','flat32'].map(v=>groups.get(split+'/'+v));assert.ok(a&&b&&c);
  assert.ok(c.interiorMAE<=protocol.flat32AdoptionRatio*a.interiorMAE&&c.fullMAE<=a.fullMAE,'C32 failed registered adoption');
  gradient=gradient && ['interiorMAE','fullMAE','gradientError'].every(k=>b[k]<=protocol.gradientAdoptionRatio*a[k]) && b.edgeMAE<=a.edgeMAE+protocol.gradientEdgeAllowance;
 }
 assert.equal(e.selectedRepresentation,'flat32');
 assert.equal(e.gradientCandidate,gradient?'ACCEPTABLE_TECHNICALLY':'REJECTED_NUMERIC');
 assert.ok(Number.isInteger(e.performance.maxPatches)&&e.performance.maxPatches>0&&e.performance.maxPatches<=protocol.regionBudget);
 assert.ok(Number.isInteger(e.performance.maxSceneDom)&&e.performance.maxSceneDom>=e.performance.maxPatches);
 for(const k of ['generateMsMedian','generateMsP95'])assert.ok(Number.isFinite(e.performance[k])&&e.performance[k]>=0,k);
 for(const name of ['comparison.png','workbench.png'])assert.match(e.imageHashes[name],/^[a-f0-9]{64}$/);
 assert.ok(Array.isArray(e.limitations)&&e.limitations.length>=5,'limits must remain explicit');
}
test('S1 archived measurements cover every scene and satisfy the unmodified protocol',()=>validate(evidence));
test('S1 archive audit rejects corrupt, omitted and fabricated pass claims',()=>{
 const mutations=[
  e=>{e.metrics[0].cssVsAnalyticMAE=protocol.selectedInteriorMAE;},
  e=>{e.metrics[0].shadowIoU=.4;},
  e=>{e.metrics[0].shadowCentroidPixels=protocol.shadowCentroidPixels;},
  e=>{e.metrics[1]=structuredClone(e.metrics[0]);},
  e=>{e.metrics.pop();},
  e=>{e.failures=['intentionally failing synthetic test'];},
  e=>{e.transport='inline-debug';},
  e=>{e.artStatus='ART_PASS';},
  e=>{e.sourceDigest='not-a-hash';},
  e=>{e.counts.cssFrames=9;},
  e=>{e.comparisons.find(r=>r.split==='holdout'&&r.variant==='flat32').interiorMAE=10;},
  e=>{e.gradientCandidate='ACCEPTABLE_TECHNICALLY';},
  e=>{e.performance.maxPatches=33;}
 ];
 for(const mutate of mutations){const fake=structuredClone(evidence);mutate(fake);assert.throws(()=>validate(fake));}
});
