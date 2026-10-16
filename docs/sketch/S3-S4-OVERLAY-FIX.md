# S3/S4 interrupted-run recovery and overlay correction

2026-10-16. These are implementation repairs, not a completed stage or ART_PASS.

Actual failed run `38848174902`, source head `9304efe4b033bb7c36d246c537d9eb0b64ac1e72`:

- Baseline job `116803666523`: `ValueError: S3 contour budget exceeded` during `describe`.
- Reserved-parameter job `116803666620`: GEOS `Unable to determine overlay result geometry dimension` during tone-region intersection.
- Independent Cycles reference and radiometry had passed both jobs. The failure was in the numerical region compiler, not the workbench browser.

The trace was recovered by a bounded, read-only diagnostic run `38855362266`, job `116825485921`. Its temporary workflow is removed. An initial diagnostic failed because Python forwarded Authorization to signed storage; using an unredirected header corrected that without publishing credentials.

Repair hypothesis: zero-area line/point contacts must not be forwarded as mixed-dimensional painting regions; entirely light-visible faces should reuse their exact camera-visible area rather than accumulate round-trip transform seams. Partial light-view clipping is normalized on the existing 0.00001px precision grid, with a four-grid numerical margin clipped back to the original face. All polygon holes and disconnected areas remain; no identity-specific branch, image input or face-wide blur is added.

Regression tests cover holes/islands, mixed-dimensional contacts, empty intersections and symmetric bounded area. Original image-error thresholds, descriptor budget and 60,000-point ceiling remain unchanged. Real baseline and reserved-parameter render tests must still pass before the repair or stage is declared verified.
