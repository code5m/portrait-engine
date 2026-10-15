# Portrait Engine Master Digital Human Roadmap

> **最高优先级（不可用 UI、参数数量或 CI 代替）：研究的是通用生成能力，人物作品是验证手段，写实质量是核心衡量标准。**
>
> 原生 HTML + CSS 负责所有画像绘制，JavaScript 只提供数值计算。每次研究至少跨 3 个身份 × 3 个灯位 × 5 种表情进行技术验证；无独立真实盲评，艺术质量始终 `ART_UNVERIFIED`。正式制度：[研究宪章](RESEARCH-CONSTITUTION.md)，现有债务：[审计](ENGINE-QUALITY-AUDIT.md)。

## Vision

Portrait Engine is not intended to be only a CSS portrait demo. The long-term goal is a programmable portrait system where a human identity can be described, transformed, rendered and evaluated through explicit structure.

Pipeline:

```
Identity DNA
    ↓
Face Structure
    ↓
Volume Field
    ↓
Lighting Model
    ↓
Surface / Hair / Stroke
    ↓
Renderer
```

## Completed foundations

- Research 001-010: CSS drawing experiments, parameterization, lighting studies, stroke studies, blind evaluation framework.
- Face DNA foundation: structural description layer separated from rendering.
- GitHub research history and reproducible validation workflow.

## Phase M3: Structural Human Model

### Face DNA + Geometry

Goal:

Convert independent sliders into coordinated human structure parameters.

Modules:

- skull
- brow
- orbit
- nose
- cheek
- mouth
- jaw

Acceptance:

- old parameter files remain compatible
- new structural parameters generate stable geometry
- changes affect related facial regions together

## Phase M4: Volume and Lighting

Goal:

Move from painted shadows to coherent form.

Modules:

- volume field
- light direction
- cast shadow relationships
- graphite response

Acceptance:

- same identity remains believable under multiple lights
- shadows follow facial structure

## Phase M5: Identity Model

Goal:

Generate distinct people rather than scaled variants.

Examples:

- narrow face / deep orbit
- wide face / strong jaw
- aged face / changed soft tissue

Acceptance:

Independent observers recognize different identities.

## Phase M6: Expression DNA

Goal:

Introduce life.

Expressions:

- neutral
- happy
- sad
- angry
- thinking

Based on structural changes, not image overlays.

## Phase M7: Hair Field

Goal:

Replace hair blocks with structured growth.

Includes:

- root direction
- strand grouping
- curl behavior
- highlight response
- occlusion

## Phase M8: Skin and Artistic Surface

Goal:

Create believable portrait surfaces.

Includes:

- skin micro variation
- graphite texture
- irregular strokes
- artistic style controls

## Renderer Strategy

CSS remains the original research renderer.

Future renderers must be isolated:

- CSS Renderer
- SVG Renderer
- WebGL/WebGPU Renderer

No renderer should be presented as another renderer.

## Research rules

- CI success is engineering evidence only.
- Artistic quality requires human evaluation.
- No generated images, photos or hidden assets used as CSS results.
- Failed experiments remain documented.
