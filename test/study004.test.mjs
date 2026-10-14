import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = file => fs.readFileSync(new URL(file, import.meta.url), 'utf8');
const css = read('../styles/study004.css');
const html = read('../index.html');
const source = read('../scripts/build-standalone.py');
const browser = read('./browser-qa.py');
const workflow = read('../.github/workflows/visual-study.yml');
const output = read('../standalone.html');

test('Study 004 is the final visible layer in live page, offline build and actual browser QA', () => {
  const previous = html.indexOf('href="./styles/likeness.css"');
  const study = html.indexOf('href="./styles/study004.css"');
  assert.ok(previous > 0 && study > previous, 'Study 004 must not be hidden below the old likeness layer');
  assert.match(source, /'likeness','study004'/);
  assert.match(browser, /'likeness', 'study004'/);
  assert.ok(output.includes('Research 004: portrait form before decoration'));
  assert.doesNotMatch(output, /<link\s+rel="stylesheet"/);
});

test('Every graphite feature is an original browser primitive, never an external image', () => {
  assert.doesNotMatch(css, /(?:url\s*\(|data:image|base64|<svg|<canvas|<img|image-set\s*\()/i);
  assert.match(css, /radial-gradient\(/);
  assert.match(css, /repeating-linear-gradient\(/);
  assert.match(css, /border-radius/);
  assert.match(css, /clip-path/);
  assert.doesNotMatch(output, /<\s*(?:img|svg|canvas|picture)\b/i);
});

test('Sparse stray locks are individually inspectable and the source still has exactly two eyes', () => {
  for (const name of ['flyaway-a', 'flyaway-b', 'flyaway-c', 'flyaway-d']) {
    assert.match(html, new RegExp(`class="flyaway ${name}"`));
    assert.match(css, new RegExp(`\\.flyaway-${name.slice(-1)}\\b`));
  }
  assert.equal((html.match(/class="eye eye-(?:left|right)"/g) ?? []).length, 2);
  assert.equal((html.match(/class="nose"/g) ?? []).length, 1);
});

test('Research 004 visual evidence is routed to an artifact folder and does not pollute runtime drawing', () => {
  assert.match(read('./research-matrix.py'), /research-004/);
  assert.match(workflow, /test-results\/research-004\//);
  assert.match(workflow, /python test\/hair-probe\.py/);
  assert.doesNotMatch(html, /(?:test-results|\.png|\.jpg|\.svg)/i);
});
