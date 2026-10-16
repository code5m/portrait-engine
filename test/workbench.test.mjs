import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const read=p=>fs.readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('workbench shares one bounded CSS region painter; no alternate media',()=>{
 const source=read('workbench/renderer.mjs').replace(/\/\*[\s\S]*?\*\//g,'');
 assert.doesNotMatch(source,/createElement\(['"](?:img|svg|canvas|video)|getContext|WebGL|data:image|url\(/i);
 assert.match(source,/60000/);
 const p=JSON.parse(read('research/sketch/s2-protocol.json'));
 assert.equal(p.identities.length,6);assert.equal(p.identities.filter(x=>x.split==='holdout').length,3);
 assert.equal(p.lights.length,3);assert.equal(p.levels,24);
});
test('API docs and safety boundaries exist, human feedback cannot create ART_PASS',()=>{
 const api=JSON.parse(read('workbench/openapi.json')),s=read('workbench/server.py');
 for(const path of ['/api/v1/session','/api/v1/jobs','/api/v1/reviews','/api/v1/renders/{id}/validation'])assert.ok(api.paths[path]);
 assert.match(s,/X-CSRF-Token/);assert.match(s,/allowed_origins/);assert.match(s,/STALE_REVIEW/);assert.match(s,/queue.Queue\(maxsize=8\)/);
 assert.doesNotMatch(s,/shell=True|eval\(|exec\(/);
 assert.match(s,/ART_UNVERIFIED/);
});
test('S2 completion binds actual evidence to the current measured source',()=>{
 const l=JSON.parse(read('research/sketch/stages.json')),stage=l.stages.find(s=>s.id==='S2');
 if(stage.status!=='COMPLETE')return;
 const e=JSON.parse(read(stage.evidence));assert.equal(e.stage,'S2');assert.equal(e.status,'STRUCTURE_STUDY_COMPLETE');assert.equal(e.artStatus,'ART_UNVERIFIED');assert.equal(e.humanObservers,0);
 assert.match(e.ciCommit,/^[a-f0-9]{40}$/);assert.match(String(e.ciRun),/^\d+$/);
 const paths=JSON.parse(read('workbench/source-files.json')),hash=crypto.createHash('sha256');
 for(const p of paths.sort())hash.update(p+'\0'+read(p)+'\0');
 assert.equal(e.sourceDigest,hash.digest('hex'));
 assert.equal(e.metrics.length,18);assert.equal(new Set(e.metrics.map(x=>x.renderId)).size,18);
 const t=JSON.parse(read('research/sketch/s2-protocol.json')).thresholds;
 for(const m of e.metrics){assert.equal(m.status,'PASS');for(const k of ['fullMAE','interiorMAE','featureMAE'])assert.ok(m.metrics[k]<t[k]);assert.ok(m.metrics.silhouetteIoU>=t.silhouetteIoU);}
});
