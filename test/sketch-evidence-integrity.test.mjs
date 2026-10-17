import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';

const root=new URL('../',import.meta.url);
const readJSON=p=>JSON.parse(fs.readFileSync(new URL(p,root),'utf8'));
const bytes=p=>fs.readFileSync(new URL(p,root));
const checksum=b=>crypto.createHash('sha256').update(b).digest('hex');

test('S5 and S6 completed-stage evidence is complete, immutable and non-artistic',()=>{
  const ledger=readJSON('research/sketch/stages.json');
  const stages=['S5','S6'].map(id=>ledger.stages.find(s=>s.id===id));
  if(stages.every(s=>s.status!=='COMPLETE'))return;
  assert.ok(stages.every(s=>s.status==='COMPLETE'),'Never complete S6 before S5');
  assert.equal(ledger.artStatus,'ART_UNVERIFIED');
  assert.equal(ledger.humanReview.independentObservers,0);
  const a=readJSON(stages[0].evidence),b=readJSON(stages[1].evidence);
  assert.equal(a.ciRun,b.ciRun);
  assert.equal(a.sourceHeadCommit,b.sourceHeadCommit);
  assert.equal(a.sourceHeadCommit.length,40);
  const prefix='research/sketch/evidence/raw-surface/'+a.ciRun+'/';
  const archive=readJSON(prefix+'manifest.json');
  const summary=readJSON(prefix+'result.json');
  assert.equal(summary.status,'PASS');
  assert.equal(summary.failures.length,0);
  assert.deepEqual(summary.counts,{S5:18,S6:45});
  assert.equal(summary.artStatus,'ART_UNVERIFIED');
  assert.equal(summary.humanObservers,0);
  assert.equal(archive.run,a.ciRun);
  assert.equal(archive.sourceHead,a.sourceHeadCommit);
  assert.ok(Object.keys(archive.files).length>600,'Evidence archive was truncated');
  let pngs=0;
  for(const [path,proof] of Object.entries(archive.files)){
    assert.ok(path.startsWith(prefix)||path===stages[0].evidence||path===stages[1].evidence,'Unexpected evidence path');
    assert.ok(!path.split('/').some(s=>s==='..'||s==='.'),'Unsafe evidence path');
    const value=bytes(path);
    assert.equal(value.length,proof.bytes,'Evidence file length changed: '+path);
    assert.equal(checksum(value),proof.sha256,'Evidence hash changed: '+path);
    if(path.endsWith('.png')){pngs++;assert.equal(value.subarray(0,8).toString('hex'),'89504e470d0a1a0a');}
  }
  assert.ok(pngs>=63,'Expected every measured scene to have an original PNG');
  for(const [stage,evidence,n] of [['S5',a,18],['S6',b,45]]){
    assert.equal(evidence.stage,stage);
    assert.equal(evidence.status,'TECHNICAL_STUDY_COMPLETE');
    assert.equal(evidence.metrics.length,n);
    assert.equal(evidence.counts.scenes,n);
    assert.equal(evidence.imageArchiveAvailable,true);
    assert.equal(evidence.artStatus,'ART_UNVERIFIED');
    assert.equal(evidence.humanObservers,0);
    assert.equal(evidence.humanReview,'DEFERRED_BY_OWNER');
    assert.equal(new Set(evidence.metrics.map(m=>m.id)).size,n);
    assert.equal(evidence.rawReports.length,n/3);
    assert.ok(archive.files[evidence.uiEvidence],'Missing frozen real UI evidence');
    for(const report of evidence.rawReports){
      assert.ok(archive.files[report],'Missing raw case report '+report);
      const r=readJSON(report);
      assert.equal(r.status,'PASS');
      assert.equal(r.stage,stage);
      assert.equal(r.humanObservers,0);
      assert.equal(r.artStatus,'ART_UNVERIFIED');
      assert.equal(r.ciRun,a.ciRun);
      assert.equal(r.sourceHeadCommit,a.sourceHeadCommit);
    }
  }
});
