# Research 004 — Making the face readable before adding detail

**State:** Engineering/experimental pass; **artistic photorealism NOT validated**.
**Scope:** The original CSS-only portrait, not an AI-generated or photograph-derived image.
**Baseline:** GitHub `main` commit `4911d3efc3aeb2793570282339cf513cd2ee2f1a` (Research 003).

## Question

Will reducing occlusion from solid hair shapes, strengthening upper eyelid and alar plane edges, and abandoning uniformly gridded paper give a more legible face **without** switching from CSS to source images, SVG or Canvas?

## What was changed

- Added a dedicated, last-applied `styles/study004.css` layer, rather than silently rewriting the prior research layer. All previous geometry and nine adjustable parameters still apply.
- Rebuilt the upper hair cap, rear hair and four near-cheek locks with narrower, asymmetric outlines; supplemented them with four independently inspectable, sparse CSS flyaway lines.
- Prototyped four *temporary* CSS hair opacity strategies in a real Chromium browser, chose a light-ink foreground to expose the ear and zygomatic silhouette, and saved a reproducible trial script (`test/hair-probe.py`).
- Redrew the eyelid/iris overlap for more visible gaze, softened the nasal highlight into a small graded bridge and asymmetric alar shadows, refined the lips and faded the neck into paper.
- Replaced the conspicuously periodic paper grid with offset, low-opacity CSS stippling. No texture image or network resource has been introduced.

## Evidence and method

Run after `npm run verify`:

```bash
python3 test/browser-qa.py
python3 test/research-matrix.py
python3 test/hair-probe.py
```

Generated (not committed, and never used as runtime assets) under `test-results/research-004/`:

- `contact-sheet.png`: nine real browser captures (80/100/120% face width by -60/0/+60-degree light), with geometry and visible lighting differences tested.
- `hair-alternatives.png`: controlled four-way comparison (dark foreground / almost clear / selected light ink / washed graphite).
- `hair-measurements.json`: grayscale counts, not a beauty score.
- `before-after.png` and `comparison-metrics.json`: a local paired crop against the same settings in Research 003.

The former baseline's dark pixel fraction is **0.3268**, versus **0.1577** in Research 004, for grayscale pixels below 90 in the same `[50,72,414,500]` crop with face width 100% and centered light. This means much less near-black surface blocks the cheeks, **not** that realism has doubled. Whole-paper mean absolute per-channel pixel differences are approximately 16.8/16.6/15.9 (0–255); pixel difference likewise does **not** certify aesthetic improvement.

## Verdict

Better cheek/ear legibility and brighter drawing silhouette in a controlled 2D sketch. But the portrait still has a graphic, airbrushed look: artificial eye whites, uniform cranium geometry and insufficient natural ink gesture. **Not accepted as professional graphite portrait**. We do not claim that this is a new physical-lighting renderer, anatomical face mesh or generalizable human identity generator.

## Deliberately rejected approaches

- More opaque hair locks increased helmet/curtain appearance.
- Almost transparent hair locks made the head feel disconnected from the hairstyle.
- Relying on color averages or passing CI as the art benchmark. Formal independent human/artist assessment remains pending.

## Next research decision

Instead of adding another hundred CSS gradients blindly: isolate one facial region (especially the orbit or mouth), compare a small set of separately reasoned native-CSS shape topologies, and solicit external blind preference ratings when practical. If progressively finer CSS shapes do not improve human ratings, design an **explicitly named, separately testable SVG backend** with the same parameter contract rather than misrepresenting SVG imagery as CSS.
