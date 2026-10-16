# S3/S4 interrupted-run recovery and overlay correction

2026-10-16. These are implementation repairs, not a completed stage or ART_PASS.

Actual failed run `38848174902`, source head `9304efe4b033bb7c36d246c537d9eb0b64ac1e72`:

- Baseline job `116803666523`: `ValueError: S3 contour budget exceeded` during `describe`.
- Reserved-parameter job `116803666620`: GEOS `Unable to determine overlay result geometry dimension` during tone-region intersection.
- Independent Cycles reference and radiometry had passed both jobs. The failure was in the numerical region compiler, not the workbench browser.

The trace was recovered by a bounded, read-only diagnostic run `38855362266`, job `116825485921`. Its temporary workflow is removed. An initial diagnostic failed because Python forwarded Authorization to signed storage; using an unredirected header corrected that without publishing credentials.

Repair hypothesis: zero-area line/point contacts must not be forwarded as mixed-dimensional painting regions; entirely light-visible faces should reuse their exact camera-visible area rather than accumulate round-trip transform seams. Partial light-view clipping is normalized on the existing 0.00001px precision grid, with a four-grid numerical margin clipped back to the original face. All polygon holes and disconnected areas remain; no identity-specific branch, image input or face-wide blur is added.

## Follow-up: S4 has the same mixed-dimension boundary problem

Run `38855617842`, source `df033795d3ff10867d81f2dc754f22297a7cbfc8`, reserved job `116826535960`: `reserved-d-left` compiled S3 control/tone/masses with 30635/29815/3676 contour points. S4 then failed at `visible.boundary.difference(...)`: a mixed GeometryCollection has no boundary object. This is a recorded failure, not a passing reserved matrix. The other shard was not yet completed at diagnosis.

S4 now takes boundaries from the normalized painted area for camera-visible regions, silhouette and semantic controls; the original S2 Projection object is not mutated. A synthetic triangle plus detached line/point must produce exactly the same S4 descriptor as the triangle alone. Existing hole/island and commutative-intersection regressions remain.

CI enumerates all six identities directly from the frozen S2 protocol, runs their three lights as six parallel shards, and requires every shard plus the real workbench in an all-scenes gate. The selector is included in both stage source digests. This changes scheduling, not samples, light conditions or thresholds. Reserved samples already exposed during debugging are reserved-parameter regressions, not an untouched blind generalization study.

Original image-error thresholds, descriptor budget and 60,000-point ceiling remain unchanged. Full measured reports, screenshots and UI results are still required before a stage is declared verified. Artifact storage quota failures are not proof that image archives exist; numerical receipts are also printed to CI logs for subsequent durable repository archival.
