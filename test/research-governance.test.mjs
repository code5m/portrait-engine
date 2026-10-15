import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { IDENTITIES } from '../src/identity/identity-registry.mjs';
import { deriveEngineStyle, buildFaceState } from '../src/engine.mjs';
import { EXPRESSION_PRESETS } from '../src/expression/expression-dna.mjs';
import { deriveIdentityFormStyle, deriveContourPolygon } from '../src/anatomy/identity-contour.mjs';
import { validatePromotionEvidence } from '../scripts/validate-human-evidence.mjs';

const file=path=>fs.readFileSync(new URL('../'+path,import.meta.url),'utf8');
const IDS=IDENTITIES.map(i=>i.id),LIGHTS=['front','side','top'],EXPRESSIONS=Object.keys(EXPRESSION_PRESETS);
const proof=style=>[
  style['--fg-leftEye-x'],style['--fg-rightEye-x'],
  style['--fg-noseBase-y'],style['--fg-leftJaw-x'],
  style['--fg-rightJaw-x'],style['--dna-skull-height']
].join(' : ');

test('governing principle and auditable R012 / R013 statuses are explicit',()=>{
 const doc=file('docs/RESEARCH-CONSTITUTION.md'),ledger=JSON.parse(file('research/experiments.json'));
 assert.match(doc,/研究的是通用生成能力，人物作品是验证手段，写实质量是核心衡量标准/);
 assert.deepEqual(ledger.experiments.map(e=>e.id),['R012','R013']);
 assert.equal(ledger.renderer,'HTML_CSS_ONLY');
 assert.equal(ledger.overallArtStatus,'ART_UNVERIFIED');
 assert.equal(ledger.experiments[0].status,'REJECTED_FIRST_VIEW');
 assert.equal(ledger.experiments[1].status,'ART_UNVERIFIED');
});

test('unregistered identities demonstrate geometry generality without new one-off CSS',()=>{
 const base=IDENTITIES[0].faceDNA;
 const newDNA=[{skull:{width:.04,height:.9},cheek:{volume:.8},jaw:{width:.07,angle:.2}},
  {skull:{width:.95,height:.3},cheek:{volume:.08},jaw:{width:.85,angle:.72}},
  {orbit:{width:.06,depth:.99},nose:{base:.91,projection:.25}},
  {nose:{base:.14,projection:.91},mouth:{width:.85},brow:{depth:.24}}]
  .map(change=>({...base,...change}));
 // A nose/eye-only DNA mutation should change those organs, NOT the skull outline.
 const allDNA=[...IDENTITIES.map(x=>x.faceDNA),...newDNA];
 const signatures=allDNA.map(d=>{
   const s=deriveIdentityFormStyle(d);
   return [deriveContourPolygon(d),s['--r013-eye-scale-x'],s['--r013-eye-scale-y'],
           s['--r013-nose-scale-x'],s['--r013-nose-scale-y'],s['--r013-mouth-scale-x']].join('|');
 });
 assert.equal(new Set(signatures).size,signatures.length,'new DNA produced an identical structural face signature');
 assert.equal(deriveContourPolygon(newDNA[2]),deriveContourPolygon(newDNA[3]),
   'changing nose/orbit/mouth must NOT reshape the skull silhouette');
 const styles=newDNA.map(x=>deriveIdentityFormStyle(x));
 assert.ok(styles.every(s=>s['--r013-head-contour'].startsWith('polygon(')));
 assert.notEqual(styles[0]['--r013-jaw-intensity'],styles[1]['--r013-jaw-intensity']);
});

test('3 x 3 x 5 technical matrix preserves DNA through lighting and expression',()=>{
 let count=0;
 const signatures=new Set();
 for(const identity of IDENTITIES){
   const primary=buildFaceState({id:identity.id,faceDNA:identity.faceDNA,lighting:{mode:'front'}});
   const anchor=proof(deriveEngineStyle(primary));
   const faceShape=deriveContourPolygon(identity.faceDNA);
   for(const mode of LIGHTS)for(const [name,expression] of Object.entries(EXPRESSION_PRESETS)){
     const state={...primary,lighting:{mode},expression};
     const one=deriveEngineStyle(state), two=deriveEngineStyle(state);
     assert.deepEqual(one,two,'non-deterministic CSS surface');
     assert.equal(proof(one),anchor,'lighting/expression contaminated face identity');
     assert.equal(deriveContourPolygon(state.faceDNA),faceShape,'head silhouette changed without DNA change');
     assert.ok(Object.values(one).every(s=>!String(s).includes('NaN')&&!String(s).includes('Infinity')));
     assert.ok(one['--expr-mouth-open']&&one['--v-cheekLeft-shade']);
     signatures.add(identity.id+':'+mode+':'+name);
     count++;
   }
 }
 assert.equal(count,45);
 assert.equal(signatures.size,45);
});

test('opt-in researcher variants never switch page renderer default by JS assignment',()=>{
 const app=file('src/app.mjs');
 assert.match(app,/const formStudy = qs\.get\('r012'\) === 'form';/);
 assert.match(app,/const identityStudy = qs\.get\('r013'\) === 'anatomy';/);
 assert.match(app,/if \(formStudy\) root\.dataset\.r012 = 'form'/);
 assert.match(app,/if \(identityStudy\) root\.dataset\.r013 = 'anatomy'/);
 assert.equal((app.match(/Object\.entries\(deriveEngineStyle\(activeCharacter\)\)/g)||[]).length,1,
   'full canonical engine must be computed exactly once per render update');
});

const dimensions=['realism','anatomy','volume','skinHair','eyeExpression','identity','generalization'];
function simulatedReview(phase,offset=0){
 const scenes=IDS.flatMap(identity=>LIGHTS.flatMap(light=>['neutral','happy'].map(expression=>({
   identity,light,expression,preference:'candidate',
   baseline:Object.fromEntries(dimensions.map(x=>[x,2])),
   candidate:Object.fromEntries(dimensions.map(x=>[x,3]))
 }))));
 return {phase,sessions:Array.from({length:5},(_,i)=>({
   reviewerPseudonym:'syntheticTest_'+offset+'_'+i,selfReportedHumanAdult:true,
   observations:structuredClone(scenes)
 }))};
}
test('synthetic human-score fixture only exercises parser, never counts as real art pass',()=>{
 const fake={schemaVersion:1,experimentId:'R014',protocol:'paired-blind-v1',
  studyPreregistration:'Synthetic data MUST NEVER be submitted as real observation.',
  recruitmentAndConsent:'Only test fixture, not collected or consented human evidence.',
  reviewSets:[simulatedReview('discovery'),simulatedReview('replication',1)]};
 const parsed=validatePromotionEvidence(fake,'IN_MEMORY_SYNTHETIC_ONLY');
 assert.equal(parsed.stages.length,2);
 assert.match(parsed.authenticity,/MANUAL_SOURCE_VERIFICATION_REQUIRED/);
 assert.throws(()=>validatePromotionEvidence({...fake,reviewSets:[fake.reviewSets[0]]}),
   /replication/);
 const duplicate=structuredClone(fake);
 duplicate.reviewSets[1].sessions[0].reviewerPseudonym=duplicate.reviewSets[0].sessions[0].reviewerPseudonym;
 assert.throws(()=>validatePromotionEvidence(duplicate),/repeated across phases/);
 const low=structuredClone(fake);
 for(const set of low.reviewSets)for(const session of set.sessions)
   for(const obs of session.observations)obs.candidate.realism=obs.baseline.realism;
 assert.throws(()=>validatePromotionEvidence(low),/realistic-quality improvement/);
});
