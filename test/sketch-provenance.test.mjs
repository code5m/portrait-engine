import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
test('completed sketch evidence has valid digests, unique scenes and finite measurements',()=>{
 for(const s of read('research/sketch/stages.json').stages){
  if(s.status!=='COMPLETE')continue;
  const e=read(s.evidence);
  assert.match(e.sourceDigest,/^[a-f0-9]{64}$/);
  assert.match(e.ciCommit,/^[a-f0-9]{40}$/);
  if(e.sourceHeadCommit)assert.match(e.sourceHeadCommit,/^[a-f0-9]{40}$/);
  assert.equal(new Set(e.metrics.map(m=>m.scene)).size,e.metrics.length);
  for(const m of e.metrics)for(const [key,value] of Object.entries(m)){
   if(key.endsWith('MAE'))assert.ok(Number.isFinite(value)&&value>=0,key);
  }
  for(const hash of Object.values(e.imageHashes||{}))assert.match(hash,/^[a-f0-9]{64}$/);
  if(s.id==='S0'){
   assert.equal(Object.keys(e.imageHashes).length,23);
   assert.equal(e.counts.blenderPrimitives,9);assert.equal(e.counts.cssPrimitives,9);
   assert.equal(e.counts.cssThreeTone,3);assert.equal(e.counts.referenceHeadFrames,2);
   assert.ok(e.freestylePixelDelta>0.01);
  }
 }
});
