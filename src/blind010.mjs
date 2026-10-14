/** Research 010: preregistered, privacy-preserving blinded CSS paint comparison.
 * Pure protocol code: usable by the study UI, browser test, analyzer, and CLI.
 * Browser captures and synthetic tests are NOT human aesthetic evidence.
 */
export const PROTOCOL = 'portrait-engine-r010-blind';
export const VERSION = 1;
export const VARIANTS = Object.freeze(['tonal', 'strokes']);
export const METRICS = Object.freeze(['orbit', 'nose', 'structure', 'graphite', 'credibility']);
export const SCENES = Object.freeze([
  Object.freeze({ id: 'left-light', lightDirection: -60 }),
  Object.freeze({ id: 'frontal-light', lightDirection: 0 }),
  Object.freeze({ id: 'right-light', lightDirection: 60 })
]);
export const CONTROLLED = Object.freeze({
  faceWidth: 100, eyeSpacing: 0, noseWidth: 100, jaw: 100,
  graphite: 65, hatching: 62, hairVolume: 100, mouthWidth: 100
});
export const HUMAN_MIN = 5;

function requireCondition(ok, why) { if (!ok) throw new Error(why); }
const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
const object = x => x && typeof x === 'object' && !Array.isArray(x);
const median = xs => { const s = [...xs].sort((a,b)=>a-b); return s.length % 2 ? s[(s.length-1)/2] : (s[s.length/2-1] + s[s.length/2])/2; };
const round = n => Math.round(n * 1000) / 1000;

/** Inject random bytes to make order testable without changing browser randomization. */
export function makeTrialPlan(bytes) {
  requireCondition(bytes && bytes.length >= 4 && [...bytes].every(x=>Number.isInteger(x) && x>=0 && x<=255), 'Four random bytes required');
  const order = [...SCENES];
  for (let i=order.length-1;i>0;i--) {
    const j = bytes[2-i] % (i+1);
    [order[i],order[j]] = [order[j],order[i]];
  }
  const startWithStrokes = bytes[2] % 2 === 1;
  return Object.freeze(order.map((scene,index) => Object.freeze({
    sceneId: scene.id,
    lightDirection: scene.lightDirection,
    left: (index % 2 === 0) === startWithStrokes ? 'strokes' : 'tonal',
    right: (index % 2 === 0) === startWithStrokes ? 'tonal' : 'strokes'
  })));
}

function validateTrial(t) {
  requireCondition(object(t), 'Each trial must be an object');
  const scene = SCENES.find(x=>x.id===t.sceneId);
  requireCondition(scene && t.lightDirection===scene.lightDirection, 'Unrecognized or modified light scene');
  requireCondition(object(t.fixed) && Object.keys(CONTROLLED).length===Object.keys(t.fixed).length &&
    Object.entries(CONTROLLED).every(([key,val])=>t.fixed[key]===val), 'Fixed subject parameters changed');
  requireCondition(Array.isArray(t.candidates) && t.candidates.length===2, 'Each trial needs two candidates');
  requireCondition(t.candidates[0].label==='A' && t.candidates[1].label==='B', 'Blind labels A/B required');
  requireCondition(new Set(t.candidates.map(x=>x.variant)).size===2 &&
    t.candidates.every(x=>VARIANTS.includes(x.variant)), 'Invalid or duplicate paint variants');
  for (const c of t.candidates) {
    requireCondition(object(c.scores) && Object.keys(c.scores).length===METRICS.length &&
      METRICS.every(key=>hasOwn(c.scores,key)&&Number.isInteger(c.scores[key])&&c.scores[key]>=1&&c.scores[key]<=5),
      'Every candidate needs five integer scores in 1..5');
  }
  requireCondition(['A','B','tie'].includes(t.preference), 'A, B or tie preference required');
  return t;
}

/** Only complete self-declared human records enter the evaluation cohort.
 * This validates provenance claims; it CANNOT authenticate humans/independence.
 */
export function validateResponse(x) {
  requireCondition(object(x), 'A rating JSON object is required');
  requireCondition(x.protocol===PROTOCOL && x.version===VERSION, 'Incompatible protocol/version');
  requireCondition(x.source==='self_reported_human' && x.independent===true, 'Automated or undeclared responses are excluded');
  requireCondition(typeof x.sessionId==='string' && /^[a-z0-9-]{16,64}$/i.test(x.sessionId), 'Random session id required');
  requireCondition(typeof x.createdAt==='string' && !Number.isNaN(Date.parse(x.createdAt)), 'ISO recording time required');
  requireCondition(Array.isArray(x.trials) && x.trials.length===SCENES.length, 'Three fully scored light scenes required');
  const seen = new Set();
  for (const trial of x.trials) {
    validateTrial(trial);
    requireCondition(!seen.has(trial.sceneId), 'Duplicate scene');
    seen.add(trial.sceneId);
  }
  requireCondition(SCENES.every(scene=>seen.has(scene.id)), 'Missing required light scene');
  return x;
}

export function createResponse({ sessionId, trials, createdAt = new Date().toISOString(), independent }) {
  const result = { protocol:PROTOCOL,version:VERSION,source:'self_reported_human',
    independent:independent === true,sessionId,createdAt,trials };
  validateResponse(result);
  return result;
}

/** Three correlated trials are reduced to ONE vote + one mean delta per observer. */
export function summarize(records) {
  requireCondition(Array.isArray(records), 'An array of submissions is required');
  const used = new Set();
  const rejected = [];
  const reviewers = [];
  for (const [i, raw] of records.entries()) {
    try {
      const x = validateResponse(raw);
      requireCondition(!used.has(x.sessionId), 'Duplicate session id');
      used.add(x.sessionId);
      const choices = {tonal:0,strokes:0,tie:0};
      const deltas = Object.fromEntries(METRICS.map(m=>[m,[]]));
      for (const t of x.trials) {
        const a = t.candidates.find(c=>c.variant==='tonal');
        const b = t.candidates.find(c=>c.variant==='strokes');
        for (const metric of METRICS) deltas[metric].push(b.scores[metric]-a.scores[metric]);
        choices[t.preference==='tie'?'tie':t.candidates.find(c=>c.label===t.preference).variant]++;
      }
      const vote = choices.strokes>choices.tonal?'strokes':choices.tonal>choices.strokes?'tonal':'tie';
      reviewers.push({vote,deltas:Object.fromEntries(METRICS.map(m=>[m,round(deltas[m].reduce((a,b)=>a+b,0)/SCENES.length)]))});
    } catch (e) {
      rejected.push({index:i+1,reason:String(e.message).slice(0,120)});
    }
  }
  const n=reviewers.length;
  const votes = {tonal:0,strokes:0,tie:0};
  for (const r of reviewers) votes[r.vote]++;
  const medianDeltas = Object.fromEntries(METRICS.map(m=>[m,n?round(median(reviewers.map(r=>r.deltas[m]))):null]));
  let decision='INSUFFICIENT_HUMAN_EVIDENCE';
  if (n>=HUMAN_MIN) {
    if (votes.strokes/n>=0.75 && medianDeltas.credibility>=1 &&
      ['orbit','nose','structure'].every(key=>medianDeltas[key]>=-0.5)) decision='PROMISING_NEEDS_REPLICATION';
    else if (votes.tonal/n>=0.6) decision='STROKES_NOT_SUPPORTED';
    else decision='NO_DEMONSTRATED_ART_GAIN';
  }
  return {
    protocol:'portrait-engine-r010-summary',version:VERSION,
    evaluatedSessions:n,rejectedCount:rejected.length,rejected,
    observerVotes:votes,medianPerObserverScoreDeltaStrokesMinusTonal:medianDeltas,
    decision,minObservers:HUMAN_MIN,comparisonBaseline:'tonal',productionDefault:'unchanged',
    independenceVerified:false,statisticalSignificanceClaimed:false,
    note:'A signed-in browser or exported JSON cannot prove reviewer identity, independence, or artistic quality. The experiment baseline is tonal; the public default remains unchanged.'
  };
}
