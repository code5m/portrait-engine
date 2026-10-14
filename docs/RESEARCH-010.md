# Research 010 - Independent blind comparison of R008 tonal shading and R009 form strokes

**Protocol status: IMPLEMENTED / ENGINEERING CHECKS PASSED LOCALLY / ART_UNVERIFIED.**
The research issue is [#4](https://github.com/code5m/portrait-engine/issues/4). Human submissions at the time of implementation: **zero**. A successful headless browser test, green CI, or a valid JSON schema is not a human aesthetic assessment.

## Research question and preregistration

Does the *strokes* option (`r009=strokes`) improve the artistic credibility of the same original CSS portrait versus the *tonal* option (`r009=tonal`) at identical light, geometry, rendering dimensions, and graphite settings? The public portrait does **not** change. These are two experimental modes sharing the R008 face surface model; neither is automatically made the default.

The comparison uses the **frozen Research 009 renderer** from GitHub commit `f6e948855ad65d2f03fd981be41d162686a623c4`, Git blob `673e76657792a3c808c4a51c4f0f09c659624b9f`. The exact same blob is linked in GitHub at `study/010-renderer.html`. This is intentionally a **pinned experimental snapshot** (not a second actively maintained renderer). It prevents future changes to `standalone.html` from silently invalidating the study. The snapshot is one original 100% DOM/CSS HTML file; no SVG, Canvas, image URLs, photos, or AI-generated painting assets are substituted.

## Controlled three-scene protocol

| Parameter | Fixed value |
| --- | --- |
| Lighting | -60 degrees, 0 degrees, +60 degrees (all required) |
| faceWidth, jaw, noseWidth, mouthWidth, hairVolume | 100, 100, 100, 100, 100 |
| eyeSpacing, graphite, hatching | 0, 65, 62 |
| Candidate presentation | Two 410 x 535 CSS-pixel iframes, no user interaction inside |
| Candidate painting techniques | tonal (R008), strokes (R009) |
| Rating metrics (both candidates) | eye socket and gaze; nose volume; cheek/jaw/skull coherence; graphite feel; human portrait credibility |
| Rating range | integers from 1 to 5 for each of 5 criteria, both candidates |
| Preference choice | candidate A, candidate B, or tie (per light scene) |

The three light-scene order is randomly permuted per session. Left/right identity is hidden and alternates; variants are randomized across sessions. The client waits for both live CSS portraits to render and verifies the `r009` mode and all nine slider positions before permitting a score. This is a **limited single-blind evaluation**: researchers and sufficiently technical observers can inspect URL/source. Therefore the protocol tells observers to avoid browser developer tools and discussions, and does not claim double blinding.

The rating page [study/010-blind.html](../study/010-blind.html) neither uploads nor stores ratings in a database, local storage, or cookies. After three fully scored scenes, an observer must check an explicit self-report and voluntarily download their JSON. The file contains only a random session ID, timestamp, controlled conditions, anonymous A/B candidate mapping and scores. No name, address, login, or network identifiers are intentionally collected. The evaluator independently decides whether to send that JSON to the researcher. **The browser cannot verify human identity or observer independence.**

### Distribute without giving anyone private GitHub access

The repository also contains **two fully standalone HTML deliverables**, generated deterministically from the pinned CSS renderer and the same protocol source:

- `study/010-blind-offline.html`: send this one local HTML file to each independent observer; double-click/open it in a normal browser, complete all three lighting conditions, and export the anonymous JSON. No GitHub login, HTTP server, external assets, internet, or application installation is needed.
- `study/010-results-offline.html`: open this one local HTML file on the researcher's computer, select the voluntarily received JSON files, and export an aggregate. The page has **zero external network requests**; individual raw session identifiers are excluded from the aggregate.

```bash
python3 scripts/build-r010-study.py          # rebuild both portable HTML files
python3 scripts/build-r010-study.py --check  # byte-for-byte reproducibility gate
```

The builder checks the frozen Git blob SHA and fails rather than silently updating the research stimulus. `npm run verify` includes the offline-output equality gate. The headless browser checks offline iframe rendering and verifies that there are no network requests.

### Run the study directly from the repository

```bash
# In the repository root:
python3 -m http.server 4173
# Visit: http://127.0.0.1:4173/study/010-blind.html
```

The pinned renderer and modules are loaded from the same origin. Serving via HTTP is required for reliable ES module/iframe access; opening `file://` may be blocked by browsers. On a narrow device each visual iframe retains 410 CSS pixels, with horizontal scrolling isolated to its preview panel. Device pixel ratios may differ; record device type during a future extended study if strict cross-device calibration is necessary.

## Preregistered evaluation logic

All submitted files are reviewed **locally**, without uploads, through [study/010-results.html](../study/010-results.html) or:

```bash
node scripts/analyze-r010.mjs ./voluntary-anonymous-ratings/ --out aggregate.json
```

The analyzer rejects unsupported protocol versions, incomplete scenes, modified face parameters, non-integer/out-of-range ratings, duplicate scene IDs, malformed files, automation provenance, and duplicate random session IDs (first accepted session only). An anonymous ID cannot detect two different sessions from one person; the researcher must coordinate observers independently.

The three correlated lighting judgments are reduced to **one preference vote per observer**, not three independent people. Five quality deltas are also reduced to one per-person average delta (strokes minus tonal) across the three lights, followed by the median across observers. The aggregate reports accepted and rejected counts, preference votes, median per-observer differences, and explicit uncertainty. It does **not** compute a p-value, pretend to know the true distribution of observers, or infer photorealism from a small sample.

Decision thresholds, fixed **before** receiving any volunteer scores:

1. **Fewer than 5 self-declared independent human observers**: `INSUFFICIENT_HUMAN_EVIDENCE` - cannot decide.
2. With at least five observers: **at least 75%** prefer strokes (per-observer majority across lights), the median overall credibility improvement is **at least 1 point** on the 1..5 scale, and no median eye/nose/structure delta is below -0.5: `PROMISING_NEEDS_REPLICATION`. This is **not** proof of a statistically significant improvement or sufficient reason to change production default.
3. Otherwise, if **at least 60%** prefer tonal: `STROKES_NOT_SUPPORTED` - do not pursue form-stroke embellishment as an artistic improvement.
4. Otherwise: `NO_DEMONSTRATED_ART_GAIN` - mixed/tied/weak results; retain the baseline pending better evidence.

No status automatically modifies the production/default portrait. The independent art review remains open after any green engineering gate.

## Technical QA and real evidence boundaries

Run:

```bash
npm run verify
python3 test/study010-visual.py
```

The Node tests cover randomized balance, immutable light scenes, schema and format validation, duplicate-session rejection, privacy-preserving aggregation, early-decision rejection, and positive/negative/tie decision paths. Browser QA loads real CSS frames, checks both variants and all fixed parameters in all three scenes, exercises score/export and local analyzer, checks mobile dimensions, and deletes all synthetic downloaded responses. It writes reproducible Chromium scene screenshots and `metrics.json` under `test-results/research-010/` for CI evidence.

Some sandboxed local Chromium builds block even localhost navigation. In that case QA uses an explicitly reported `inlineFallback` with the same real CSS/JS rendered in headless Chromium, not fake screenshots. **GitHub Actions must navigate the real local HTTP integration** and will fail if it falls back. If a future CI job fails, preserve the failure evidence; do not claim full end-to-end success.

## Limitations and research direction

Human feedback count remains 0 unless actual voluntary observer submissions are provided. The default subject is a visibly stylized, somewhat mask-like human head. This evaluation can judge *comparative* preference; it cannot by itself establish professional photorealism. Observer independence, deception, accessibility, screen color calibration, and generalization to other faces require broader follow-up studies. If the R009 stroke candidate is not favored, stop adding decorative stroke layers and return to a principled redesign of skull shape, eye sockets and facial proportions.

**Research ideal:** treat the browser as a medium for explanatory, controllable visual expression; never confuse elaborate CSS, automated tests, or color differences with a human portrait that genuinely moves a viewer.
