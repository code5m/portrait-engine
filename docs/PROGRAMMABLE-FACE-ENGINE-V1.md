# Programmable Face Engine V1 — implementation contract

## P1–P8 (engineering closure candidate)

The default portrait editor now consumes a canonical Face DNA model. Nine legacy sliders remain a backward-compatible UI adapter, and the existing Research 005–010 A/B query routes keep their original painting behavior. The renderer still uses HTML and native CSS only: no face bitmap, SVG, Canvas, or 3D mesh.

```
identity registry -> Face DNA -> canonical 16 landmark geometry
                                     -> shared relief / surface field
expression DNA ----------------------> geometry styling
hair field --------------------------> native CSS strand styling
skin / artistic surface -------------> native CSS material styling
lighting rig -> volume + surface + stroke fields -> native CSS renderer
```

- P1: `face-dna.mjs`, `face-geometry.mjs`, `engine.mjs` define the single canonical structural pipeline.
- P2: three IDs are `lin-che`, `zhou-qishan`, and `third-portrait` (the latter is an experimental synthetic character, not a photo likeness).
- P3: five independent continuous expression parameter sets; this is a CSS approximation, not FACS-certified muscle simulation.
- P4: deterministic procedural hair root/direction/length/density field sampled in JS; browser draws stylistic strokes in CSS, **not individual physical hairs**.
- P5: parametric tone, roughness, pore and paper/stroke strength; the resulting material is stylistic, **not physically based or SSS skin**.
- P6: front, side, top, cinematic, custom share one azimuth/elevation light.
- P7: automated `3 identities × 3 lights` plus five expressions numeric invariants, with browser screenshots planned as artifact-only evidence. A matching checksum is not proof of realistic resemblance.
- P8: `npm run verify`, GitHub Actions, tracked standalone export, and continuous architecture notes.

## File protocols

`portrait-engine-params/v1` JSON remains accepted and still uses nine numbers. A new `portrait-engine-character/v2` JSON carries identity ID, Face DNA, expression, hair, skin, lighting, legacy slider adapter and a stable DNA fingerprint. The importer rejects a mismatched fingerprint.

The editor stores legacy values at `portrait-engine/parameters/v1` and the complete character at `portrait-engine/character/v2`, entirely in the browser. There is no network upload.

## Acceptance scope

Structural reproducibility, browser interaction and deterministic CSS paint are engineering goals. Photorealism, anatomical validity, realistic hair synthesis, true human identity likeness and emotional acting **remain unverified**. The Research 010 ART_UNVERIFIED state must not be changed without independent human evidence.
