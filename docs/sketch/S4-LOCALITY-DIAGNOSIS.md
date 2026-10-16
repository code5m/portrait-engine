# S4 local-edge diagnosis and visibility repair

2026-10-16. Continuation of `S3-S4-OVERLAY-FIX.md` and `S3-S4-RENDER-FIX.md`. No completed-stage claim is made here.

## Actual failure retained

Run `38859002187`, head `abfccf9e8adedd258af69979224937c1459afef7`, job `116836824423`: head-c completed all three numerical compilations and all S3 checks passed. S4 left/front/right still failed: outside-edge maximum 20/11/14 gray levels; ink fractions 0.122643/0.124026/0.123770. The 0.12 cap and <=1 outside tolerance are unchanged. Other jobs have their own outcomes; this is not a claim that this run finished all 18 scenes or the UI.

## Controlled browser diagnosis

Run `38860468155`, job `116841352850`, source head `81ca0244b086c5c2b3cb4506179b585a4683ce14`. The diagnostic reused hash-verified head-c descriptors and rendered fresh independent reference images. Critical source digests were S3 `c25117a73a9478dacd110f849bfda228db16d6e037d529678bef2b8563a10d01` and S4 `a4e722935811036749cf7e07bd58b6ceb81269b69dd9e9b2ca9c1342e8dd6bbc`.

The same selected edge rings were drawn with the old bridged polygon and then native CSS shape() subpaths. No geometry, selected rings, widths, opacity or allowed margin changed. Left/front/right outside-selected counts were 38/13/32 with polygon, and 0/0/0 with shape. Maximum outside changes were 20/11/14 versus 0/0/0. Separate hard-only and soft-only shape ablations also had zero outside change in all three lights. Some old polygon ghost pixels were more than six pixels from any selected ring, not legitimate feathering.

This proves a rendering defect in the bridge serialization for these complex ribbons. It does NOT prove full S4 success: shape-only combined ink fractions remained 0.1207983193/0.1229760197/0.1216181595, still above 0.12. Diagnostic workflow success is not a stage receipt.

S4 now serializes edge ink as real independent CSS subpaths, with holes and disconnected parts preserved, no connecting bridge and no SVG/Canvas/image fallback. The immutable S2/S3 tone painter is untouched. Unsupported CSS shape() raises an explicit dependency error; the validated browser is Chromium 140. Browser subpath/hole/gap and input-rejection regressions are run before head compilation. The diagnostic remains available on workflow_dispatch, not as a completion gate.

## Visibility-supported creases

Code audit found two mismatches with the registered contrast-supported edge hypothesis:

1. The old contrast used unshadowed `scene['shaded']` even when S3 had blocked direct light. The corrected face mean weights the existing S3 lit and unlit branches by camera-visible area. Fully occluded direct light cannot create a crease; full visibility preserves the old lit mean. This remains a face-mean approximation, not a continuous edge-local integral.
2. The old crease segment was intersected with the union of two adjacent visible faces; a fully hidden neighbor could still contribute a crease. Require both visible sides at the shared edge. One-sided camera boundaries remain represented by the separate hard occlusion/silhouette pass.

Synthetic controls reproduce both defects without any identity selection. All angle, contrast, width, opacity, feather, point-count, pixel-error and ink-area thresholds remain unchanged. The next all-six-identity run must determine whether these implementation repairs satisfy the original gates.

## Durable evidence, separate from ZIP artifacts

Actions ZIP uploads have failed due to storage quota. Successful shards will now pack only allowlisted exact reports, PNGs and reference metadata. The all-scenes job rechecks the full cohort and actual temporary-test UI receipt before creating a new evidence-only Git branch. It never moves the PR or main ref and never publishes credentials. Every file has a checksum; PNG hashes match the actual measured captures. Six parser/security regressions use temporary synthetic data and cannot publish an archive. Evidence is not claimed available until the publisher actually succeeds and its new Git tree is verified.
