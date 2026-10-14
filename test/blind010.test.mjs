import test from 'node:test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';
import { CONTROLLED, METRICS, SCENES, makeTrialPlan, validateResponse, createResponse, summarize } from '../src/blind010.mjs';
const mk = (id, winner='strokes', options={}) => {
  const plan=makeTrialPlan([0,1,0,55]);
  return createResponse({sessionId:`session-${String(id).padStart(16,'0')}`,independent:true,createdAt:'2026-10-14T04:00:00.000Z',trials:plan.map(scene=>({
    sceneId:scene.sceneId,lightDirection:scene.lightDirection,fixed:{...CONTROLLED},
    candidates:[
      {label:'A',variant:scene.left,scores:Object.fromEntries(METRICS.map(m=>[m,scene.left===winner?5:2]))},
      {label:'B',variant:scene.right,scores:Object.fromEntries(METRICS.map(m=>[m,scene.right===winner?5:2]))}
    ],preference:winner==='tie'?'tie':scene.left===winner?'A':'B'
  }))});
};
const copy=x=>structuredClone(x);

test('balanced randomized study with three unique fixed light scenes',()=>{
  for(const bytes of [[0,0,0,0],[1,2,1,255],[200,71,14,10]]){
    const plan=makeTrialPlan(bytes);
    assert.equal(plan.length,3);
    assert.deepEqual(new Set(plan.map(t=>t.sceneId)),new Set(SCENES.map(s=>s.id)));
    assert.deepEqual(new Set(plan.map(t=>t.lightDirection)),new Set([-60,0,60]));
    assert.ok(plan.every(t=>new Set([t.left,t.right]).size===2));
    assert.equal(plan.filter(t=>t.left==='strokes').length>=1,true);
    assert.equal(plan.filter(t=>t.left==='strokes').length<=2,true);
  }
  assert.notDeepEqual(makeTrialPlan([0,0,0,0]),makeTrialPlan([0,0,1,0]));
});
test('randomness failure is explicit, never silently deterministic',()=>{
  assert.throws(()=>makeTrialPlan([]));assert.throws(()=>makeTrialPlan([0,-1,5,6]));
});
test('valid anonymous self-declared human response covers all 3 scenes',()=>{
  const x=mk(1);
  assert.equal(validateResponse(x),x);
  assert.equal(x.trials.length,3);
  assert.ok(x.trials.every(t=>t.candidates.every(c=>METRICS.every(m=>c.scores[m]>=1&&c.scores[m]<=5))));
});
test('reject missing, changed and duplicated experimental conditions',()=>{
  const original=mk(1);
  for(const change of [
    x=>x.trials.pop(),
    x=>x.trials[1].sceneId=x.trials[0].sceneId,
    x=>x.trials[0].lightDirection=33,
    x=>x.trials[0].fixed.jaw=111,
    x=>x.trials[0].fixed.extra=1,
    x=>x.trials[0].candidates[1].variant=x.trials[0].candidates[0].variant
  ]){const x=copy(original);change(x);assert.throws(()=>validateResponse(x));}
});
test('reject fake or malformed rating provenance, scores, votes and session',()=>{
  const original=mk(1);
  for(const change of [
    x=>x.source='automation',x=>x.independent=false,
    x=>x.sessionId='1',x=>x.trials[2].preference='C',
    x=>x.trials[0].candidates[0].scores.orbit=2.5,
    x=>x.trials[0].candidates[0].scores.orbit=6,
    x=>delete x.trials[0].candidates[0].scores.credibility
  ]){const x=copy(original);change(x);assert.throws(()=>validateResponse(x));}
});
test('no human data means no aesthetic conclusion',()=>{
  const s=summarize([]);assert.equal(s.evaluatedSessions,0);
  assert.equal(s.decision,'INSUFFICIENT_HUMAN_EVIDENCE');
  assert.equal(s.medianPerObserverScoreDeltaStrokesMinusTonal.credibility,null);
  assert.equal(s.comparisonBaseline,'tonal');
  assert.equal(s.productionDefault,'unchanged');
});
test('three lighting trials from one person are counted as one observer',()=>{
  const s=summarize([mk(1),mk(1),mk(2)]);
  assert.equal(s.evaluatedSessions,2);
  assert.equal(s.rejectedCount,1);
  assert.deepEqual(s.observerVotes,{tonal:0,strokes:2,tie:0});
  assert.equal(s.decision,'INSUFFICIENT_HUMAN_EVIDENCE');
});
test('pre-registered positive threshold only says promising and needs replication',()=>{
  const s=summarize([mk(1),mk(2),mk(3),mk(4),mk(5)]);
  assert.equal(s.evaluatedSessions,5);
  assert.equal(s.decision,'PROMISING_NEEDS_REPLICATION');
  assert.equal(s.medianPerObserverScoreDeltaStrokesMinusTonal.credibility,3);
  assert.equal(s.statisticalSignificanceClaimed,false);
});
test('majority for old tonal baseline retires stroke experiment',()=>{
  const s=summarize([mk(1,'tonal'),mk(2,'tonal'),mk(3,'tonal'),mk(4,'strokes'),mk(5,'strokes')]);
  assert.equal(s.decision,'STROKES_NOT_SUPPORTED');
  assert.deepEqual(s.observerVotes,{tonal:3,strokes:2,tie:0});
});
test('ties and split votes cannot be interpreted as verified artistic improvement',()=>{
  const s=summarize([mk(1,'tie'),mk(2,'tonal'),mk(3,'strokes'),mk(4,'tie'),mk(5,'strokes')]);
  assert.equal(s.decision,'NO_DEMONSTRATED_ART_GAIN');
});
test('invalid and duplicate files are excluded with explicit reasons; no crash',()=>{
  const s=summarize([mk(1),{not:'json'},mk(1),null,mk(2)]);
  assert.equal(s.evaluatedSessions,2);assert.equal(s.rejectedCount,3);
  assert.ok(s.rejected.every(x=>x.reason));
});

test('CLI summarizes locally, excluding raw session identifiers from output',()=>{
  const dir=mkdtempSync(join(tmpdir(),'portrait-r010-'));
  try {
    const response=mk(5);
    writeFileSync(join(dir,'observer.json'),JSON.stringify(response));
    const output=execFileSync(process.execPath,['scripts/analyze-r010.mjs',dir],{encoding:'utf8'});
    const result=JSON.parse(output);
    assert.equal(result.evaluatedSessions,1);
    assert.equal(result.decision,'INSUFFICIENT_HUMAN_EVIDENCE');
    assert.equal(output.includes(response.sessionId),false);
  } finally {rmSync(dir,{recursive:true,force:true});}
});

test('immutable Research 010 portrait renderer equals audited R009 Git blob',()=>{
  const bytes=readFileSync('study/010-renderer.html');
  const prefix=Buffer.from(`blob ${bytes.length}\0`);
  const hash=createHash('sha1').update(prefix).update(bytes).digest('hex');
  assert.equal(hash,'673e76657792a3c808c4a51c4f0f09c659624b9f');
});
