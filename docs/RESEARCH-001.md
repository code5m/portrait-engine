# Research 001 - Geometry coherence and controllable graphite light

## Hypothesis

Adding more gradients without coordinating anatomical landmarks produces a more polished doll, not a more credible portrait. The first research result should couple face contour, ear location, hair silhouette, mouth size and key-light direction, with deterministic checks at the parameter extremes.

## Implemented

1. A pure, inspectable mapping function derives CSS custom properties from validated portrait parameters (`src/geometry.mjs`).
2. The face contour and both ears move around the same center. Hair mass follows the face silhouette proportionally without losing the separate hair-volume control.
3. A two-dimensional value model moves the primary highlight, facial shadow, temple strength and nose cast shadow as the virtual key light travels from left to right.
4. Mouth width is adjustable; a CSS-only anatomy guide view exposes eye, nose and mouth landmarks without affecting portrait parameters.
5. Both new numerical parameters import legacy JSON v1 data without discarding saved portraits.
6. The offline HTML is built *before* the node test gate; the CI step checks whether the committed bundle is reproducible.

## Limits / honest interpretation

- This is a stylized two-dimensional shading approximation, NOT real light transport.
- A single identity remains the basis; three presets alone are NOT three independently generated real people.
- Construction guide placements and head proportions remain artistic approximations, not certified anatomical measurements.
- Repeating CSS strokes do not yet capture the variation of a trained graphite artist.
- CSS masks and gradients need validation across rendering engines. Passing Node or Chromium tests cannot certify art quality.

## Study protocol

Compare baseline / left-lit / right-lit images at the same viewport with identical presets. Verify the dominant shadow changes sides and nose/light highlights do not jump across facial features. At faceWidth=80 and =120 inspect that ears meet the silhouette and hair still covers the forehead naturally. Avoid rewarding sheer layer count; assess believable volume and intentional pen-stroke rhythm.

Next: restructure eyes, zygomatic/mandible planes and hair strokes into a small reusable landmark model, run systematic browser screenshots plus human aesthetic assessment, and then only consider higher-level portrait identity controls.
