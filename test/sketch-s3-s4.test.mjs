import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
const json=p=>JSON.parse(read(p));
test('S3/S4 are explicit API stages and preserve the frozen S2 painter',()=>{
 const server=read('workbench/server.py'),renderer=read('workbench/study_renderer.mjs');
 assert.match(server,/STAGES=\('S2','S3','S4'\)/);assert.match(server,/descriptor_digest/);
 assert.match(renderer,/import \{draw as drawBase, clipPath\} from '\.\/renderer.mjs'/);
 assert.doesNotMatch(renderer,/getContext\(|createElement\(['"](?:canvas|svg|img)|data:image/);
 assert.doesNotMatch(renderer,/target\.style\.filter/);
 assert.match(read('workbench/app.mjs'),/payload=\{light:.*stage:pipeline.value/);
});
test('stages cannot claim completion without actual full-coverage evidence',()=>{
 const ledger=json('research/sketch/stages.json');
 for(const stage of ['S3','S4']){
  const s=ledger.stages.find(x=>x.id===stage);if(s.status!=='COMPLETE')continue;
  const e=json(s.evidence);assert.equal(e.stage,stage);assert.equal(e.artStatus,'ART_UNVERIFIED');assert.equal(e.humanObservers,0);
  assert.equal(e.status,'TECHNICAL_STUDY_COMPLETE');assert.match(String(e.ciRun),/^\d+$/);assert.match(e.ciCommit,/^[a-f0-9]{40}$/);
  const paths=json('research/sketch/'+stage.toLowerCase()+'-sources.json');const hash=crypto.createHash('sha256');
  for(const p of paths.sort())hash.update(p+'\0'+read(p)+'\0');assert.equal(e.sourceDigest,hash.digest('hex'));
  assert.equal(e.metrics.length,18);assert.equal(new Set(e.metrics.map(x=>x.id)).size,18);
  for(const row of e.metrics){assert.equal(row.status,'PASS');assert.deepEqual(row.failures,[]);}
  if(stage==='S3'){
   const limits=json('research/sketch/s3-protocol.json').thresholds;
   for(const r of e.metrics){for(const k of ['fullMAE','interiorMAE','featureMAE'])assert.ok(r.metrics[k]<limits[k]);assert.ok(r.metrics.silhouetteIoU>=limits.silhouetteIoU);}
  }else{
   const p=json('research/sketch/s4-protocol.json');
   for(const r of e.metrics){assert.ok(r.inkFraction<=p.maxInkFraction);assert.ok(r.outsideAllowedChange<=p.outsideEdgePixelTolerance);assert.ok(r.classification.lost>0);}
  }
 }
});
