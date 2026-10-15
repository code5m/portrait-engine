/**
 * Portrait Engine research policy gate. No third-party packages are required.
 *
 * Static checks are defense-in-depth, NOT proof that the image looks human.
 * Runtime browser request/DOM checks live in research-governance-matrix.py.
 */
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root = process.cwd();
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const list = (folder, ext) => fs.readdirSync(path.join(root, folder), {withFileTypes: true})
  .flatMap(entry => entry.isDirectory()
    ? list(path.join(folder, entry.name), ext)
    : entry.name.endsWith(ext) ? [path.join(folder, entry.name)] : []);
const stripCSS = value => value.replace(/\/\*[\s\S]*?\*\//g, ' ');
const violations = [];
const reject = (condition, where, message) => {
  if (condition) violations.push(where + ': ' + message);
};

for (const file of list('styles', '.css')) {
  const css = stripCSS(read(file));
  reject(/\burl\s*\(/i.test(css),file,'CSS url() may load images/fonts; portrait renderer must draw with CSS primitives');
  reject(/(?:-webkit-)?image-set\s*\(/i.test(css),file,'image-set() is forbidden');
  reject(/@import\b/i.test(css),file,'remote/imported CSS is forbidden in drawing source');
  reject(/(?:^|[;:{\s])(?:-webkit-)?paint\s*\(/i.test(css),file,'Houdini paint() is not CSS-native drawing');
}
for (const file of list('src', '.mjs')) {
  const js = read(file).replace(/\/\*[\s\S]*?\*\//g, ' ');
  const forbidden = [
    [/\b(?:OffscreenCanvas|createImageBitmap|WebGLRenderingContext|WebGL2RenderingContext|GPUCanvasContext)\b/, 'pixel/canvas/WebGL API'],
    [/\b(?:new\s+Image|new\s+XMLHttpRequest)\s*\(/, 'image or remote load constructor'],
    [/\b(?:getContext|drawImage|getImageData|putImageData|toDataURL|transferToImageBitmap)\s*\(/, 'canvas drawing API'],
    [/\bcreateElement\s*\(\s*['"](?:img|canvas|svg|video|picture|iframe|object|embed)['"]\s*\)/, 'image/canvas/svg element creation'],
    [/\b(?:fetch|importScripts)\s*\(/, 'runtime remote/resource import in renderer'],
  ];
  for (const [pattern, label] of forbidden) reject(pattern.test(js),file,label);
}
const html = read('index.html');
const start = html.indexOf('id="portrait"'), end = html.indexOf('<div class="drawing-signature"');
reject(start < 0 || end < start,'index.html','missing explicit facial drawing subtree');
const portrait = html.slice(start,end);
reject(/<(?:img|svg|canvas|picture|video|iframe|object|embed)\b/i.test(portrait),'index.html','non-HTML/CSS media is forbidden inside portrait');
const standalone = read('standalone.html');
reject(/<(?:img|svg|canvas|picture|video|iframe|object|embed)\b/i.test(standalone),'standalone.html','embedded drawing media disallowed');
reject(/<(?:script|link)[^>]+(?:src|href)\s*=/i.test(standalone),'standalone.html','standalone must not require remote drawing resources');
reject(/(?:url\s*\(|image-set\s*\(|@import\b)/i.test(stripCSS(standalone.replace(/<script[\s\S]*?<\/script>/g,''))),'standalone.html','external CSS painting asset');
const ledger = JSON.parse(read('research/experiments.json'));
assert.equal(ledger.schemaVersion,1);
assert.equal(ledger.renderer,'HTML_CSS_ONLY');
assert.equal(ledger.overallArtStatus,'ART_UNVERIFIED','No art certification without independently authenticated observers');
assert.ok(Array.isArray(ledger.experiments) && ledger.experiments.length>=2);
const statuses = new Set(['ART_UNVERIFIED','REJECTED_FIRST_VIEW','PROMISING_NEEDS_REPLICATION','ART_VERIFIED_WITH_INDEPENDENT_EVIDENCE']);
const seen = new Set();
const app = read('src/app.mjs');
const allCSS = list('styles','.css').map(read).join('\n');
for (const e of ledger.experiments) {
  assert.match(e.id,/^R\d{3}$/);
  assert.ok(!seen.has(e.id),'duplicate research number: '+e.id);
  seen.add(e.id);
  assert.ok(statuses.has(e.status),e.id+' bad research status');
  assert.equal(e.optIn,true,e.id+' must remain opt-in');
  assert.ok(typeof e.hypothesis==='string'&&e.hypothesis.length>=24,e.id+' requires falsifiable hypothesis');
  assert.ok(e.minimumIdentities>=3 && e.minimumLightingConditions>=3 && e.minimumExpressions>=5,e.id+' needs multi-person conditions');
  const short = e.id.slice(1).toLowerCase();
  assert.ok(e.candidateQuery.startsWith('?r'+short+'='),e.id+' wrong query parameter');
  assert.ok(app.includes("qs.get('r"+short+"')"),e.id+' requires explicit experiment activation');
  assert.ok(allCSS.includes('[data-r'+short+'='),e.id+' should use uniquely scoped CSS');
  assert.ok(typeof e.evidenceDocument==='string' && fs.existsSync(path.join(root,e.evidenceDocument)),e.id+' missing research document');
  if (e.status === 'ART_VERIFIED_WITH_INDEPENDENT_EVIDENCE') {
    assert.ok(fs.existsSync(path.join(root,'research/promotions',e.id+'.json')),e.id+' cannot self-promote without paired human evidence');
  }
}
for (const file of list('styles','.css').filter(p=>/research\d{3}\.css$/i.test(p))) {
  const id = path.basename(file).match(/(\d{3})/)[1];
  reject(!seen.has('R'+id),file,'research mode omitted from experiment ledger');
  reject(/\[\s*data-identity\s*=/i.test(read(file)),file,'identity-specific painted CSS is overfitting, not generic generation');
}
for (const file of list('test','.py').filter(p=>/research\d{3}-preview\.py$/i.test(p))) {
  const id = path.basename(file).match(/(\d{3})/)[1];
  reject(!seen.has('R'+id),file,'visual experiment omitted from ledger');
}
reject((app.match(/Object\.entries\(deriveEngineStyle\(activeCharacter\)\)/g)||[]).length!==1,'src/app.mjs','canonical engine style must be derived exactly once per apply()');
if (violations.length) {
  console.error('RESEARCH_POLICY_FAIL:\n'+violations.map(x=>' - '+x).join('\n'));
  process.exitCode=1;
} else {
  console.log('RESEARCH_POLICY_ENGINE_PASS: CSS-only media, registered opt-in studies, no per-identity CSS, single canonical style writer');
  console.log('ART_UNVERIFIED: static policy is NOT a human realism evaluation');
}
