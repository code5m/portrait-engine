# Research 002 | Graphite planes rather than wallpaper texture

## Question

Can pure HTML + CSS gain more plausible facial volume by splitting the
face into anatomical planes and driving regional hatch density from the same
key-light model, without using image assets, SVG or Canvas?

## Evidence and observations

- **Baseline:** stylized face, repeated high-contrast parallel hair stripes,
  overly circular iris, a glowing spherical nose tip, minimal cheek volume.
- **Revised:** a brow ridge, orbital recess, cheekbone and mandible planes
  are independently drawn via CSS gradients and feathered elliptical masks.
  Nasal side and tip values are softened and the iris/lower lip reduced.
- **Mark-making:** face, jaw, orbital, cheek and nasal regions each have
  localized hatching masks and independently oriented stroke directions.
  Hair has a stronger overall dark value and a few fine curved sweep lines.
- **Geometry:** a centralized drawing-coordinate landmark helper allows
  testable proportions while adjusting width, ears, hair mass and eye span.
- **Nine cases:** width 80/100/120 percent crossed with light -60/0/+60
  degrees. Headless Chromium produced a PNG and DOM measurement report for
  each case. The light-source extremes result in distinct pixels and a
  mirror-consistent light/shadow variable order, with no eye crossing or
  unexpected portrait horizontal overflow. Tests also check mobile width.
- **Pipeline:** one offline HTML build embeds original CSS and local JS;
  no remote files are needed. Reproducible build continues to gate CI.

## Does it look better?

Some aspects are less mechanical than Research 001: the white spherical nose
highlight was reduced, the hair texture now relies more on a broad dark mass,
and face shading follows common key-light values. **But this is only a
qualified improvement**: the eyes are still too symmetric, the hair outline
is still oversized, skin gradients are too smooth, and the lips remain
geometric. The result is still closer to a polished illustration than a
skilled graphite drawing. Automated PASS is not an art grade.

This evaluation is based on direct inspection of Chromium screenshots; there
is no independent artist blind-test evidence, no quantitative photo realism
score, and no multi-engine pixel-consistency check. Do not advertise these.

## Repeatable protocol

```bash
npm run verify
python3 test/browser-qa.py
python3 test/research-matrix.py
```

The matrix writes `test-results/research-002/contact-sheet.png` and
`measurements.json`. The screenshots are **QA evidence**, never consumed
by the portrait renderer and intentionally not committed as runtime assets.

## Next experiment (not yet implemented)

Instead of more color gradients, trial changes to the underlying face
silhouette and perceptual proportions: upper eye-lid corner geometry,
realistic hairline recession, asymmetric mouth corners, alar cartilage and
controlled cheek/jaw turning. Establish a human visual panel before adding
more presets or AI. If CSS makes art-specific details too brittle, research a
**separate SVG rendering backend** using the same parameter contract without
misrepresenting it as a pure-CSS drawing.

**Research verdict: PASS for reproducible structure/lighting experiment;
NOT PASSED for naturalistic graphite portrait quality.**
