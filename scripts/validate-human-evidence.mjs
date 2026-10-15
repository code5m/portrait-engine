/**
 * Structural validator for independent A/B observations. An automated parser
 * CANNOT authenticate that an observer was a real human. Provenance and real
 * consent must be independently reviewed before visual-promotion approval.
 *
 * At least 5 unique observers per study + a separate replication study,
 * 3 identities x 3 lights x 2 expressions per observer, with seven 1..5
 * paired dimensions. No names, addresses, or emails should be committed.
 */
import fs from 'node:fs';
import path from 'node:path';

const IDS = ['lin-che','zhou-qishan','third-portrait'];
const LIGHTS = ['front','side','top'];
const EXPRESSIONS = ['neutral','happy'];
const DIMS = ['realism','anatomy','volume','skinHair','eyeExpression','identity','generalization'];
const expected = new Set(IDS.flatMap(identity =>
  LIGHTS.flatMap(light => EXPRESSIONS.map(expression => [identity,light,expression].join('/')))));
const median = array => {
  const s=[...array].sort((a,b)=>a-b);
  return s.length % 2 ? s[(s.length-1)/2] : (s[s.length/2-1]+s[s.length/2])/2;
};
const fail = message => { throw new Error('HUMAN_EVIDENCE_INVALID: '+message); };
const validRating = v => Number.isInteger(v) && v>=1 && v<=5;

/**
 * This only guards against missing/incomplete/badly structured datasets.
 * Honest study provenance MUST be checked by an independent human.
 */
export function validatePromotionEvidence(data, filename='unknown') {
  const check = (value,reason) => { if (!value) fail(filename+': '+reason); };
  check(data?.schemaVersion===1,'unsupported protocol');
  check(/^R\d{3}$/.test(data.experimentId??''),'invalid experiment id');
  check(data.protocol==='paired-blind-v1','unknown registered protocol');
  check(typeof data.recruitmentAndConsent==='string' && data.recruitmentAndConsent.length>=30,
    'human recruitment/consent procedure must be documented');
  check(typeof data.studyPreregistration==='string' && data.studyPreregistration.length>=15,
    'human A/B hypothesis must be preregistered');
  check(Array.isArray(data.reviewSets)&&data.reviewSets.length>=2,'need primary + independent replication sets');
  const globalPseudonyms=new Set();
  const stageStats=[];
  for (const set of data.reviewSets) {
    check(['discovery','replication'].includes(set.phase),'expected independent phase names');
    check(Array.isArray(set.sessions)&&set.sessions.length>=5,'need >=5 independent observers per phase');
    const preference=[];
    const improvement=[];
    const anatomy=[];
    const identity=[];
    for (const observer of set.sessions) {
      check(typeof observer.reviewerPseudonym==='string' &&
            /^[a-zA-Z0-9_-]{8,80}$/.test(observer.reviewerPseudonym),
            'anonymous reviewer pseudonym must not be email/person name');
      check(!globalPseudonyms.has(observer.reviewerPseudonym),
            'one person must not be repeated across phases');
      globalPseudonyms.add(observer.reviewerPseudonym);
      check(observer.selfReportedHumanAdult===true,
            'independent human adult affirmation missing; not independently authenticated');
      check(Array.isArray(observer.observations)&&observer.observations.length===expected.size,
            'all 3 identities x 3 lights x 2 expressions must be rated');
      const observed = new Set();
      let votes=0;
      const realismGains=[], anatomyGains=[], identityGains=[];
      for (const scene of observer.observations) {
        const key=[scene.identity,scene.light,scene.expression].join('/');
        check(expected.has(key)&&!observed.has(key),'missing/duplicated/unregistered scene '+key);
        observed.add(key);
        check(scene.preference==='candidate'||scene.preference==='baseline'||scene.preference==='tie',
              'invalid blind comparison preference');
        if(scene.preference==='candidate')votes++;
        for (const metric of DIMS) {
          check(validRating(scene.baseline?.[metric])&&validRating(scene.candidate?.[metric]),
                'incomplete paired scores for '+metric+'/'+key);
        }
        realismGains.push(scene.candidate.realism-scene.baseline.realism);
        anatomyGains.push(scene.candidate.anatomy-scene.baseline.anatomy);
        identityGains.push(scene.candidate.identity-scene.baseline.identity);
      }
      preference.push(votes>expected.size/2);
      improvement.push(median(realismGains));
      anatomy.push(median(anatomyGains));
      identity.push(median(identityGains));
    }
    check(preference.filter(Boolean).length/set.sessions.length>=.75,
          'fewer than 75% of independent observers preferred the candidate in '+set.phase);
    check(median(improvement)>=1,'median realistic-quality improvement is less than +1 in '+set.phase);
    check(median(anatomy)>=0&&median(identity)>=0,'face anatomy or identity is regressing in '+set.phase);
    stageStats.push({phase:set.phase,observers:set.sessions.length,
                     preferenceRate:preference.filter(Boolean).length/set.sessions.length,
                     realismMedianGain:median(improvement),
                     anatomyMedianGain:median(anatomy),identityMedianGain:median(identity)});
  }
  check(new Set(stageStats.map(x=>x.phase)).size===2,
        'discovery and independent replication phases are both required');
  return {id:data.experimentId,stages:stageStats,
    authenticity:'MANUAL_SOURCE_VERIFICATION_REQUIRED_NOT_PROVEN_BY_CI'};
}
export function collectPromotionEvidence(root=process.cwd()) {
  const folder=path.join(root,'research','promotions');
  if (!fs.existsSync(folder))return [];
  const records=[];
  for (const name of fs.readdirSync(folder).filter(x=>x.endsWith('.json'))) {
    const data=JSON.parse(fs.readFileSync(path.join(folder,name),'utf8'));
    const result=validatePromotionEvidence(data,name);
    if (name!==result.id+'.json')fail(name+': file and study id mismatch');
    records.push(result);
  }
  return records;
}
if (process.argv[1]&&path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname)) {
  try {
    const result=collectPromotionEvidence();
    console.log('HUMAN_EVIDENCE_STRUCTURE_PASS: '+result.length+' reviewed datasets; human authenticity cannot be verified by CI');
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(error.message);
    process.exitCode=1;
  }
}
