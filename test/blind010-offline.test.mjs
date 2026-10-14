import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const path='study/';
const blind=readFileSync(path+'010-blind-offline.html','utf8');
const results=readFileSync(path+'010-results-offline.html','utf8');
const renderer=readFileSync(path+'010-renderer.html');
const gitHash=createHash('sha1').update('blob '+renderer.length+'\0').update(renderer).digest('hex');

test('R010 offline blind and aggregation are generated from the pinned R009 renderer',()=>{
  assert.equal(gitHash,'673e76657792a3c808c4a51c4f0f09c659624b9f');
  assert.ok(blind.includes('const INLINED_HTML = '));
  assert.ok(blind.includes('frame.srcdoc=INLINED_HTML'));
  assert.ok(blind.includes('const researchEmbed = true'));
});

test('R010 standalone HTML pages need no external CSS, fonts or JS at runtime',()=>{
  for(const page of [blind,results]){
    assert.doesNotMatch(page,/<script[^>]*\bsrc\s*=/i);
    assert.doesNotMatch(page,/<link[^>]*\bhref\s*=/i);
    assert.doesNotMatch(page,/\bfetch\s*\(/i);
    assert.doesNotMatch(page,/\bXMLHttpRequest\b/);
  }
});

test('R010 offline links remain within the optional two-file distribution kit',()=>{
  assert.match(blind,/href="010-results-offline.html"/);
  assert.match(results,/href="010-blind-offline.html"/);
  assert.doesNotMatch(blind, /href="010-results.html"/);
  assert.doesNotMatch(results, /href="010-blind.html"/);
  assert.match(blind,/const HUMAN_MIN = 5/);
  assert.match(results,/INSUFFICIENT_HUMAN_EVIDENCE/);
});
