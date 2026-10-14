# Programmable Face Engine V1

## Vision

Portrait Engine 从 CSS 人像实验进入程序化人物引擎阶段。

目标不是增加 CSS 图层，而是建立：

Face DNA
↓
Structure Geometry
↓
Volume Field
↓
Lighting Model
↓
Surface / Hair / Stroke
↓
Renderer

## Completed foundation

- CSS-only portrait renderer
- Parameter system
- Face DNA experimental model
- Geometry abstraction
- Visual study pipeline
- GitHub research history

## V1 Implementation Scope

### 1. Face Structure

建立统一面部结构：

- skull
- brow
- orbit
- nose
- cheek
- mouth
- jaw

所有渲染参数必须来源于结构模型。

### 2. Volume Field

建立二维体积近似：

- forehead plane
- orbital depth
- nose projection
- cheek volume
- jaw mass

### 3. Lighting Model

统一光照解释：

- key light direction
- shadow field
- reflected light
- graphite response

### 4. Identity Model

同一引擎生成不同人物身份：

- narrow face
- strong jaw
- deep orbit
- soft face

### 5. Expression Model

后续扩展：

- neutral
- happy
- sad
- angry
- thinking

## Quality rules

- CI 通过不代表艺术成功。
- 不使用 AI 图片替代绘制。
- SVG/WebGL 必须作为独立 renderer 实验。
- 所有失败实验保留记录。

## Success criteria

最终评价标准：

不是代码数量，而是观察者是否认为人物具有可信结构和生命感。
