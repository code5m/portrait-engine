# S3/S4 real-render failure and correction

2026-10-16. Continues `S3-S4-OVERLAY-FIX.md`; this is not a completion claim.

Run `38857104811`, measured head `8482381db99179e909157a545393ea3be2ca65ef`:

- `head-b`, job `116830978632`: all three geometric compilations finished and all S3 image/shadow tests passed. S4 failed in all three lights: outside-selected-edge differences were 51/43/31 gray levels. Front/right also exceeded the 0.12 ink-area cap (0.121666/0.121024). The original failing S4 JSON is preserved at `research/sketch/evidence/failures/38857104811-head-b-S4.json`.
- `reserved-f`, job `116830978488`: all three geometric compilations finished. The checker then threw GEOS `TopologyException: side location conflict at 62.345529680115106 37.060861623449689` while XOR-combining serialized edge rings. No completed matrix report was produced by that shard.
- Other shards must retain their own outcomes; these two failures are not a full-cohort summary. Artifact ZIP uploads still failed due to account storage quota.

## Rendering repair

S4 previously clipped the whole portrait to its silhouette after painting S3. Even empty edge layers would anti-alias the original tone pixels again. Move the silhouette clip to each ink wrapper only. The underlying S3 layers are unchanged. A synthetic ellipse/hole control in an in-memory Chromium document reproduced the old bug (2571 RGB channels changed; max difference 46); the local-layer correction changed zero channels. This local synthetic check is not a head-scene result, and its transport is not the CI file-navigation transport.

`test_study_rendering.py` adds the corresponding actual file-navigation regression before expensive head compilation. It also deliberately reapplies the old whole-face clip as a negative control. The full matrix additionally asserts that the portrait container itself has no clip-path.

## Checker repair

CSS even-odd contours may self-cross after numeric serialization, while GEOS polygon operations require valid areal geometry. Repair each ring's linework and combine the valid areas by XOR on a 1e-7 percentage precision grid. Keep holes, both self-crossing lobes and duplicate-ring cancellation. Do not convexify, inflate the selected region, change the allowed feather margin or discard a failed identity. Synthetic bow-tie/hole/duplicate tests precede real matrix evaluation.

All predeclared numeric, ink-area, point-count and outside-edge thresholds remain unchanged. Descriptors are cached immediately after successful compilation, but each use still requires fresh independent references, descriptor hash checks, actual CSS renders and UI evaluation. Cached computation is never a PASS receipt.

Next: finish all six identities x three lights and actual S3/S4 workbench operations; archive exact successful measurements plus retained failures, then update stage reports/ledger and merge only on the final verified head. ART_UNVERIFIED and zero independent human observers remain.
