import { DEFINITIONS, PRESETS, KEYS, defaults, normalize, equal, encode, decode } from './parameters.mjs';
import { zh } from './i18n.mjs';
import { derivePortraitStyle } from './geometry.mjs';
import { deriveVolumeStyle } from './volume.mjs';
import { deriveFaceStructureStyle } from './face-model.mjs';
import { deriveSurfaceFieldStyle } from './surface-field.mjs';
import { deriveStrokeFieldStyle } from './stroke-field.mjs';
import { buildFaceState, deriveEngineStyle, encodeFaceState, decodeFaceState } from './engine.mjs';
import { dnaFromLegacyParameters } from './face-dna.mjs';
import { IDENTITIES, findIdentity } from './identity/identity-registry.mjs';
import { EXPRESSION_PRESETS } from './expression/expression-dna.mjs';
import { deriveIdentityFormStyle } from './anatomy/identity-contour.mjs';

const root = document.querySelector('#portrait');
const paper = document.querySelector('#portrait-paper');
const toast = document.querySelector('#toast');
const fileInput = document.querySelector('#upload-input');
// Research 005 candidates are isolated from saved portraits.
// Public default stays baseline while external aesthetic ratings are absent.
const qs = new URLSearchParams(window.location.search);
const identityStudy = qs.get('r013') === 'anatomy';
const formStudy = qs.get('r012') === 'form';
if (formStudy) root.dataset.r012 = 'form';
if (identityStudy) root.dataset.r013 = 'anatomy';
const researchVariant = qs.get('r005');
const volumeVariant = qs.get('r006');
const faceVariant = qs.get('r007');
// Research 009 inherits the exact Research 008 surface so only paint differs.
const strokeVariant = qs.get('r009');
const strokeStudy = strokeVariant === 'tonal' || strokeVariant === 'strokes';
const surfaceVariant = strokeStudy ? 'field' : qs.get('r008');
const surfaceStudy = surfaceVariant === 'legacy' || surfaceVariant === 'field';
const faceStudy = faceVariant === 'baseline' || faceVariant === 'structured' || surfaceStudy;
// Research 006 is opt-in until independent visual quality evidence exists.
// It never changes saved nine-parameter JSON or the public default.
const volumeStudy = volumeVariant === 'volume' || volumeVariant === 'baseline' || faceStudy;
if (volumeVariant === 'volume' || faceStudy) root.dataset.r006 = 'volume';
if (faceVariant === 'baseline' || faceVariant === 'structured') root.dataset.r007 = faceVariant;
if (surfaceStudy) root.dataset.r007 = 'structured';
if (surfaceStudy) root.dataset.r008 = surfaceVariant;
if (strokeStudy) root.dataset.r009 = strokeVariant;
const acceptedResearchVariants = new Set(['baseline', 'orbital', 'expression']);
if (acceptedResearchVariants.has(researchVariant)) root.dataset.r005 = researchVariant;
const researchEmbed = qs.get('embed') === '1' && (acceptedResearchVariants.has(researchVariant) || volumeStudy);
if (researchEmbed) document.body.dataset.r005Embed = '1';
const STORAGE_KEY = 'portrait-engine/parameters/v1';
let values = defaults();
let activeCharacter = buildFaceState({parameters:values});
let selectedExpression = 'neutral';
let selectedLighting = 'custom';
let noticeTimer;

function notify(message) {
  toast.textContent = message;
  toast.classList.add('is-visible');
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => toast.classList.remove('is-visible'), 2800);
}

function localize() {
  for (const el of document.querySelectorAll('[data-t]')) {
    const phrase = zh[el.dataset.t];
    if (phrase) el.textContent = phrase;
  }
  root.setAttribute('aria-label', zh.portraitAria);
}

function buildControls() {
  for (const [key, def] of Object.entries(DEFINITIONS)) {
    const parent = document.getElementById(def.group === 'geometry' ? 'geometry-controls' : 'finish-controls');
    const row = document.createElement('div');
    row.className = 'control-row';
    const meta = document.createElement('div');
    meta.className = 'control-meta';
    const label = document.createElement('label');
    label.htmlFor = `param-${key}`;
    label.textContent = zh[key] ?? key;
    const out = document.createElement('output');
    out.htmlFor = label.htmlFor;
    out.id = `output-${key}`;
    meta.append(label, out);
    const input = document.createElement('input');
    input.id = label.htmlFor;
    input.type = 'range';
    input.min = def.min;
    input.max = def.max;
    input.step = def.step;
    input.value = values[key];
    input.dataset.key = key;
    input.setAttribute('aria-describedby', `hint-${key}`);
    input.addEventListener('input', () => {
      values = normalize({ ...values, [key]: input.valueAsNumber });
      activeCharacter = buildFaceState({...activeCharacter, faceDNA:dnaFromLegacyParameters(values,activeCharacter.faceDNA), parameters:values, lighting:selectedLighting === 'custom' ? {mode:'custom', direction:values.lightDirection} : activeCharacter.lighting});
      apply();
      persist();
    });
    const hint = document.createElement('div');
    hint.className = 'control-hint';
    hint.id = `hint-${key}`;
    hint.textContent = zh[`hint_${key}`] ?? '';
    row.append(meta, input, hint);
    parent.append(row);
  }
}

function apply() {
  if (!volumeStudy) {
    root.dataset.r006 = 'volume';
    root.dataset.r007 = 'structured';
    root.dataset.r008 = 'field';
    root.dataset.r009 = 'strokes';
    root.dataset.faceEngine = 'v1';
  }
  for (const [name, value] of Object.entries(derivePortraitStyle(values))) root.style.setProperty(name, value);
  if (volumeStudy) {
    for (const [name, value] of Object.entries(deriveVolumeStyle(values))) root.style.setProperty(name, value);
  }
  if (faceStudy) {
    for (const [name, value] of Object.entries(deriveFaceStructureStyle(values))) root.style.setProperty(name, value);
  }
  if (surfaceVariant === 'field') {
    for (const [name, value] of Object.entries(deriveSurfaceFieldStyle(values))) root.style.setProperty(name, value);
  }
  if (strokeVariant === 'strokes') {
    for (const [name, value] of Object.entries(deriveStrokeFieldStyle(values))) root.style.setProperty(name, value);
  }
  for (const selector of document.querySelectorAll('[data-identity]')) {
    const active = selector.dataset.identity === activeCharacter.id;
    selector.classList.toggle('active',active); selector.setAttribute('aria-pressed',String(active));
  }
  for (const selector of document.querySelectorAll('[data-expression]')) {
    selector.classList.toggle('active',selector.dataset.expression === selectedExpression);
    selector.setAttribute('aria-pressed',String(selector.dataset.expression === selectedExpression));
  }
  for (const selector of document.querySelectorAll('[data-light-mode]')) {
    selector.classList.toggle('active',selector.dataset.lightMode === selectedLighting);
    selector.setAttribute('aria-pressed',String(selector.dataset.lightMode === selectedLighting));
  }
  if (!volumeStudy) {
    // The canonical DNA renderer is the last writer of structural/lighting properties.
    for (const [name,value] of Object.entries(deriveEngineStyle(activeCharacter))) root.style.setProperty(name,value);
  }
  if (identityStudy && !volumeStudy) {
    const style = deriveIdentityFormStyle(activeCharacter.faceDNA, activeCharacter.lighting);
    for (const [name, value] of Object.entries(style)) root.style.setProperty(name, value);
  }
  for (const key of KEYS) {
    const def = DEFINITIONS[key];
    const input = document.getElementById(`param-${key}`);
    const out = document.getElementById(`output-${key}`);
    input.value = String(values[key]);
    out.textContent = `${values[key]}${def.unit}`;
    const fraction = (values[key] - def.min) / (def.max - def.min) * 100;
    input.style.setProperty('--progress', `${fraction}%`);
  }
  for (const preset of document.querySelectorAll('[data-preset]')) {
    const active = equal(values, PRESETS[preset.dataset.preset]);
    preset.classList.toggle('active', active);
    preset.setAttribute('aria-pressed', String(active));
  }
}

function persist() {
  if (volumeStudy) return; // No experimental paint may overwrite user portraits.
  try {
    localStorage.setItem(STORAGE_KEY, encode(values));
    localStorage.setItem('portrait-engine/character/v2',encodeFaceState(activeCharacter));
  } catch { /* Browser may block storage. */ }
}
function restore() {
  try {
    const serialized = localStorage.getItem(STORAGE_KEY);
    if (serialized) values = decode(serialized);
    const character = localStorage.getItem('portrait-engine/character/v2');
    activeCharacter = character ? decodeFaceState(character) : buildFaceState({parameters:values});
    values = activeCharacter.parameters;
    selectedLighting = activeCharacter.lighting.mode;
    selectedExpression = Object.keys(EXPRESSION_PRESETS).find(key=>JSON.stringify(EXPRESSION_PRESETS[key])===JSON.stringify(activeCharacter.expression)) ?? 'neutral';
  } catch { values = defaults(); }
}
function download() {
  const blob = new Blob([encodeFaceState(activeCharacter)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'portrait-engine-character.json';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify(zh.toastSaved);
}
async function importFile(file) {
  if (!file || file.size > 1024 * 1024) throw new Error('Invalid file size');
  const text = await file.text();
  return decodeFaceState(text);
}
function updateScale() {
  if (!paper || !root) return;
  const rect = paper.getBoundingClientRect();
  const scale = Math.min(1.06, (rect.width - 14) / 380, (rect.height - 60) / 500);
  root.style.setProperty('--portrait-scale', String(Math.max(.55, scale)));
}

function setStudyMode(mode) {
  if (!['graphite', 'structure'].includes(mode)) return;
  root.dataset.study = mode;
  for (const button of document.querySelectorAll('[data-study-mode]')) {
    const active = button.dataset.studyMode === mode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  }
}

localize();
setStudyMode('graphite');
for (const button of document.querySelectorAll('[data-study-mode]')) {
  button.addEventListener('click', () => setStudyMode(button.dataset.studyMode));
}
if (!researchEmbed && !volumeStudy) restore();
for (const button of document.querySelectorAll('[data-identity]')) {
  button.addEventListener('click',()=>{
    const identity = findIdentity(button.dataset.identity);
    if (!identity) return;
    activeCharacter = buildFaceState({...activeCharacter,id:identity.id,faceDNA:identity.faceDNA});
    values = activeCharacter.parameters; apply(); persist();
  });
}
for (const button of document.querySelectorAll('[data-expression]')) {
  button.addEventListener('click',()=>{
    selectedExpression = button.dataset.expression;
    activeCharacter = buildFaceState({...activeCharacter,expression:EXPRESSION_PRESETS[selectedExpression]});
    apply(); persist();
  });
}
for (const button of document.querySelectorAll('[data-light-mode]')) {
  button.addEventListener('click',()=>{
    selectedLighting = button.dataset.lightMode;
    activeCharacter = buildFaceState({...activeCharacter,lighting:{mode:selectedLighting,direction:values.lightDirection}});
    apply(); persist();
  });
}
buildControls();
apply();
for (const button of document.querySelectorAll('[data-preset]')) {
  button.addEventListener('click', () => {
    values = { ...PRESETS[button.dataset.preset] };
    activeCharacter = buildFaceState({parameters:values}); selectedLighting='custom'; selectedExpression='neutral';
    apply(); persist();
  });
}
document.getElementById('reset-btn').addEventListener('click', () => {
  values = defaults(); activeCharacter=buildFaceState({parameters:values}); selectedLighting='custom'; selectedExpression='neutral'; apply(); persist(); notify(zh.toastReset);
});
document.getElementById('download-btn').addEventListener('click', download);
document.getElementById('import-btn').addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', async () => {
  try {
    if (!fileInput.files?.[0]) return;
    activeCharacter = await importFile(fileInput.files[0]); values = activeCharacter.parameters; selectedLighting=activeCharacter.lighting.mode; selectedExpression='neutral';
    apply(); persist(); notify(zh.toastLoaded);
  } catch { notify(zh.toastError); }
  finally { fileInput.value = ''; }
});
document.getElementById('print-btn').addEventListener('click', () => window.print());
const architectureDialog = document.getElementById('architecture-dialog');
document.getElementById('arch-btn').addEventListener('click', () => architectureDialog.showModal());
document.getElementById('arch-close').addEventListener('click', () => architectureDialog.close());
architectureDialog.addEventListener('click', event => { if (event.target === architectureDialog) architectureDialog.close(); });
if ('ResizeObserver' in window) new ResizeObserver(updateScale).observe(paper);
window.addEventListener('resize', updateScale);
updateScale();
