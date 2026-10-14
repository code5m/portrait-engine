# Portrait Engine Research Roadmap

## Vision

Portrait Engine is not a CSS trick project. The long-term goal is exploring whether browsers can become programmable visual media where a portrait is a structured, editable object instead of a static image.

## Completed Research

- Research 001-004: CSS portrait foundation, anatomy layers, lighting and visual experiments.
- Research 005-010: eye/orbit, mouth, stroke field, blind comparison workflow and evidence-driven evaluation.

## Current Limitation

The renderer can create convincing code-based artwork, but the face still behaves like manually positioned parts. The next breakthrough requires a structural model.

## Research 011

### Face DNA Model

Introduce a structured representation:

- skull proportions
- brow ridge
- orbital depth
- nose volume
- cheek plane
- mouth volume
- jaw structure

The renderer should derive visual layers from structure rather than independent sliders.

## Future Experiments

1. CSS structural renderer
2. SVG isolated comparison renderer
3. WebGL/WebGPU volumetric renderer if required

No renderer should be misrepresented as another. Research value comes from honest comparison.

## Rules

- No AI generated images as rendering substitutes.
- No copied artwork or assets.
- CI success is engineering evidence, not artistic proof.
- Preserve failed experiments and decisions.
