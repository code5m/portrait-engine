import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = name => fs.readFileSync(new URL(`../${name}`, import.meta.url), 'utf8');

test('R005 CSS has an explicit baseline and two isolated non-raster candidates', () => {
  const css = read('styles/study005.css');
  assert.match(css, /data-r005="orbital"/);
  assert.match(css, /data-r005="expression"/);
  assert.match(css, /\.eye-socket-left/);
  assert.match(css, /\.lip-line/);
  assert.doesNotMatch(css, /url\s*\(|data:image|<svg|<canvas|<img/i);
  assert.doesNotMatch(css, /data-r005="baseline"\]/, 'baseline must stay unmodified');
});

test('query-driven experiment is read-only and cannot overwrite saved user characters', () => {
  const js = read('src/app.mjs');
  assert.match(js, /acceptedResearchVariants = new Set\(\['baseline', 'orbital', 'expression'\]\)/);
  assert.match(js, /if \(!researchEmbed\) restore\(\)/);
  assert.match(js, /root\.dataset\.r005 = researchVariant/);
  assert.match(js, /researchEmbed\) document\.body\.dataset\.r005Embed/);
});

test('blind-rating protocol has three distinct arms and requires all scored fields', () => {
  const page = read('study/005-blind.html');
  assert.match(page, /\['baseline', 'orbital', 'expression'\]/);
  assert.match(page, /crypto\.getRandomValues/);
  assert.match(page, /choice\.required = true/);
  assert.match(page, /actual_variant:variant/);
  assert.match(page, /'portrait-engine-blind-r005'/);
  assert.match(page, /no automatic transmission/i);
  assert.doesNotMatch(page, /<img\b|<svg\b|<canvas\b/i);
});

test('new CSS is included in source and the fully offline single-file build', () => {
  const page = read('index.html');
  const solo = read('standalone.html');
  assert.match(page, /href="\.\/styles\/study005\.css"/);
  assert.match(page, /href="\.\/study\/005-blind\.html"/);
  assert.match(solo, /Candidate C \(expression\)/);
  assert.match(solo, /dataset\.r005 = researchVariant/); // query-driven candidate in offline build
  assert.doesNotMatch(solo, /href="\.\/study\/005-blind\.html"/, 'a single detached HTML must not contain a dead link');
  assert.doesNotMatch(solo, /<link[^>]+href="\.\/styles/);
});
