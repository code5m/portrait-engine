import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const exists=p=>fs.existsSync(new URL('../'+p,import.meta.url));
test('stage completion requires durable evidence and a next-action record',()=>{
 const ledger=JSON.parse(read('research/sketch/stages.json'));
 assert.equal(ledger.schemaVersion,1);assert.equal(ledger.stages.length,7);
 assert.match(ledger.mission,/通用生成能力/);
 const statuses=new Set(['NOT_STARTED','READY','IN_PROGRESS','COMPLETE','BLOCKED']);
 let predecessorComplete=true;
 for(const [i,stage] of ledger.stages.entries()){
  assert.equal(stage.id,'S'+i);assert.ok(statuses.has(stage.status));
  if(stage.status!=='NOT_STARTED')assert.ok(predecessorComplete,'Do not skip unfinished prerequisite '+stage.id);
  if(stage.status==='COMPLETE'){
   assert.ok(stage.report&&exists(stage.report),'completed stage needs report');
   assert.ok(stage.evidence&&exists(stage.evidence),'completed stage needs real evidence');
   const evidence=JSON.parse(read(stage.evidence));
   assert.equal(evidence.stage,stage.id);assert.match(String(evidence.ciRun),/^\d+$/);
   assert.match(evidence.ciCommit,/^[a-f0-9]{40}$/);
   assert.ok(evidence.sourceDigest&&evidence.metrics.length>0);
   assert.match(read(stage.report),/COMPLETE/);
   if(stage.id==='S0'){
    assert.equal(evidence.status,'CALIBRATION_COMPLETE');
    const files=['research/sketch/s0-scenes.json','research/sketch/sources.lock.json','study/sketch-s0.mjs','study/sketch-s0.template.html','scripts/build-sketch-s0.py','scripts/capture-sketch-s0.py','scripts/prepare-sketch-s0.py','scripts/reference-sketch-s0.py','scripts/assess-sketch-s0.py'];
    const hash=crypto.createHash('sha256');for(const name of files.sort())hash.update(name+'\0'+read(name)+'\0');
    assert.equal(hash.digest('hex'),evidence.sourceDigest,'S0 code changed after evidence; rerun and record');
    assert.equal(evidence.artStatus,'ART_UNVERIFIED');assert.equal(evidence.humanObservers,0);
    assert.equal(evidence.metrics.length,9);
    for(const m of evidence.metrics){assert.ok(m.referenceVsAnalyticMAE<4);assert.ok(m.cssVsAnalyticMAE<6);assert.ok(m.cssVsBlenderMAE<6);}
    assert.equal(evidence.counts.baselinePortraits,9);
   }
  } else predecessorComplete=false;
 }
 assert.ok(ledger.stages.some(s=>s.id===ledger.currentStage));
 assert.match(read('docs/sketch/STATUS.md'),new RegExp(ledger.currentStage));
 assert.match(read('AGENTS.md'),/stages\.json/);
});
