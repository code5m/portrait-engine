# Research 003 - Facial likeness is a problem of shape and relationships

## Hypothesis

Can an original head portrait composed entirely from CSS primitives feel less
mechanical when **anatomical relationships, eyelid overlap, side-part silhouette
and bilateral asymmetry** are redesigned before adding more gradient layers?

This continues Research 002. The research target is expressive graphite art,
not photorealism or a product feature count.

## Changes made

1. **Eyes**: Narrowed the eye groups from the previous 62px to 57px,
   redesigned the exposed sclera into a tapered fissure, partly overlaid the
   irises with the upper lids, and gave each side a different crease, position
   and brow tilt. They are intentionally not mirrored copies.
2. **Hair / hairline**: Replaced the pointed symmetrical part with a softened,
   offset hairline, moved long locks outward to expose the cheeks, then cut
   back the oversized rear masses after viewing browser screenshots.
3. **Nose and lips**: Adjusted asymmetric nostril marks, alar and bridge
   values and avoided a pair of perfectly matching circular nose highlights;
   diminished the previously rectangular lip shadows.
4. **Skull volume**: Adjusted contour curvature and left/right cheek and
   mandible shading with the same source light model introduced earlier.
5. **Geometry**: Recalibrated the eye-center landmarks to the real CSS group
   positions; they now describe small, deliberate asymmetry instead of
   incorrectly claiming perfect bilateral symmetry.

All of this is contained in `styles/likeness.css` with comments explaining
individual decisions. No existing portrait image, SVG, Canvas or remotely
sourced texture is used. No third-party character's likeness is traced.

## Real verification, not visual self-certification

Run:

```sh
npm run verify
python3 test/browser-qa.py
python3 test/research-matrix.py
```

The nine-case matrix uses face widths 80 / 100 / 120 crossed with lights
-60 / 0 / +60. It records rendered screenshots and DOM bounding boxes,
checks eye/ear ordering, containment, light direction visible pixel changes,
mobile viewport overflow, and page errors. For Research 003 the outputs are
in `test-results/research-003/` (only QA artifacts, never runtime drawing assets).

**Important defect found during this iteration:** the earlier `embedded_page()`
Chromium test omitted the newest drawing CSS when inlining styles. Thus its
screen captures could silently be from older art. We corrected the style list
and added an assertion that no external stylesheet remains in the in-memory
page. New regression tests cover this as part of the drawing contract.

## Assessment and limitations

The eye placement and hair contour now vary deliberately between the two
sides, and the lower face is less dominated by two mirrored dark curtains.
However, the drawing **still looks like a stylized coded portrait rather than
an academically convincing graphite likeness**. In particular, the irises
and eyelids remain geometric, the nose has insufficient 3D turn, and the
skin-to-hair boundaries are still harsher than natural hair. This is a
technical and artistic exploratory PASS, **not a professional-art PASS**.

Do not use CI checks or numerical image differences as a proxy for artistic
quality. There is still no independent blind evaluation by artists or users.

## Next falsifiable study

Before adding AI, run a controlled visual trial for more accurate per-feature
silhouettes using fewer, more intentional CSS paths and self-shadow. Establish
an artist-rated blind comparison against baseline and evaluate if CSS-only
painting reaches its diminishing-returns limit. If so, prototype an *explicitly
separate* SVG rendering backend on the shared data model instead of
masquerading SVG output as CSS art.
