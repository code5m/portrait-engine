import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const root=new URL('../',import.meta.url);
const read=p=>fs.readFileSync(new URL(p,root));
const json=p=>JSON.parse(read(p));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
test('S3/S4 completed records bind all 18 scenes to actual archived PNGs and UI',()=>{
 const ledger=json('research/sketch/stages.json');
 for(const stage of ['S3','S4']){
  const entry=ledger.stages.find(s=>s.id===stage);
  assert.equal(entry.status,'COMPLETE');
  const e=json(entry.evidence);assert.equal(e.status,'TECHNICAL_STUDY_COMPLETE');
  assert.equal(e.artStatus,'ART_UNVERIFIED');assert.equal(e.humanObservers,0);
  const h=crypto.createHash('sha256');
  for(const path of json('research/sketch/'+stage.toLowerCase()+'-sources.json').sort())h.update(path+'\0').update(read(path)).update('\0');
  assert.equal(h.digest('hex'),e.sourceDigest,'Frozen measured source changed');
  assert.equal(e.metrics.length,18);assert.equal(new Set(e.metrics.map(r=>r.id)).size,18);
  assert.equal(e.rawReports.length,6);
  assert.ok(e.metrics.every(r=>r.status==='PASS'&&r.failures.length===0));
  const raw=e.rawReports.flatMap(p=>json(p).metrics);assert.deepEqual(raw,e.metrics);
  const ui=json(e.uiEvidence);assert.equal(ui.status,'PASS');assert.equal(ui.ciRun,e.ciRun);assert.equal(ui.sourceHead,e.sourceHeadCommit);
  const manifest=json('research/sketch/evidence/raw/'+e.ciRun+'/manifest.json');
  for(const [path,expected] of Object.entries(manifest.files)){
   const data=read(path);assert.equal(data.length,expected.bytes,path);assert.equal(hash(data),expected.sha256,path);
  }
 }
});
