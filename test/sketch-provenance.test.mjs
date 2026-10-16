import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const sceneFields={S0:'scene',S1:'scene',S2:'renderId',S3:'id',S4:'id'};
function validateRows(stage,rows){
 const field=sceneFields[stage];assert.ok(field,'Unregistered evidence schema '+stage);
 assert.ok(Array.isArray(rows)&&rows.length>0,'Empty measurement table');
 const ids=rows.map(row=>row[field]);
 for(const id of ids)assert.ok(typeof id==='string'&&id.length>0,'Missing '+field);
 assert.equal(new Set(ids).size,rows.length,'Duplicated measured scene');
 function values(obj){
  for(const [key,value] of Object.entries(obj)){
   if(key.endsWith('MAE'))assert.ok(Number.isFinite(value)&&value>=0,key);
   if(value&&typeof value==='object')values(value);
  }
 }
 for(const row of rows)values(row);
}
test('completed sketch evidence has valid digests, unique scenes and finite measurements',()=>{
 for(const s of read('research/sketch/stages.json').stages){
  if(s.status!=='COMPLETE')continue;
  const e=read(s.evidence);
  assert.match(e.sourceDigest,/^[a-f0-9]{64}$/);
  assert.match(e.ciCommit,/^[a-f0-9]{40}$/);
  if(e.sourceHeadCommit)assert.match(e.sourceHeadCommit,/^[a-f0-9]{40}$/);
  validateRows(s.id,e.metrics);
  for(const hash of Object.values(e.imageHashes||{}))assert.match(hash,/^[a-f0-9]{64}$/);
  if(s.id==='S0'){
   assert.equal(Object.keys(e.imageHashes).length,23);
   assert.equal(e.counts.blenderPrimitives,9);assert.equal(e.counts.cssPrimitives,9);
   assert.equal(e.counts.cssThreeTone,3);assert.equal(e.counts.referenceHeadFrames,2);
   assert.ok(e.freestylePixelDelta>0.01);
  }
 }
});
test('stage-specific schema still rejects missing, duplicated or invalid nested measurements',()=>{
 assert.throws(()=>validateRows('S2',[{scene:'wrong'}]),/Missing renderId/);
 assert.throws(()=>validateRows('S2',[{renderId:'a'},{renderId:'a'}]),/Duplicated/);
 assert.throws(()=>validateRows('S3',[{id:'a',metrics:{fullMAE:NaN}}]));
 assert.throws(()=>validateRows('S4',[{id:'a',metrics:{interiorMAE:-1}}]));
 assert.throws(()=>validateRows('S3',[]));
});
