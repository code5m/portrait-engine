import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('portrait markup contains no image, SVG or canvas element', () => {
  const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const start = html.indexOf('id="portrait"');
  const end = html.indexOf('</div>\n            <div class="drawing-signature">');
  assert.ok(start > -1 && end > start, 'Portrait drawing region must exist');
  const portrait = html.slice(start, end);
  for (const feature of ['face', 'eye eye-left', 'nose', 'mouth', 'hair-cap']) {
    assert.ok(portrait.includes('class="' + feature + '"'), feature);
  }
  assert.doesNotMatch(portrait, /<(?:img|svg|canvas|picture|video)\b/i);
});

test('portrait CSS uses native shapes and not embedded/remote images', () => {
  const css = fs.readFileSync(new URL('../styles/portrait.css', import.meta.url), 'utf8');
  assert.doesNotMatch(css, /url\s*\(/i);
  assert.match(css, /radial-gradient\(/);
  assert.match(css, /repeating-linear-gradient\(/);
  assert.match(css, /mask-image/);
});

test('self-contained demo contains no external scripts, styles or image elements', () => {
  const html = fs.readFileSync(new URL('../standalone.html', import.meta.url), 'utf8');
  assert.doesNotMatch(html, /<(?:img|svg|canvas)\b/i);
  assert.doesNotMatch(html, /<script[^>]+\bsrc=/i);
  assert.doesNotMatch(html, /<link[^>]+\bhref=/i);
  assert.match(html, /id="portrait"/);
});
