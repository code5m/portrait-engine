# Portrait Engine 技术架构

## 绘画边界

`#portrait` 是唯一的绘画根节点。头像由独立的 HTML 元素、CSS 伪元素、`border-radius`、渐变、阴影、遮罩与重复线条构成，没有头像图片、SVG 或 Canvas；JavaScript **不参与像素绘制**，仅用 CSS 变量控制结果。

## 结构分层

- 后层：头发后部、耳朵、颈部及纸张。
- 中层：脸型、眼窝、眼睛、眉毛、鼻梁、嘴唇、阴影。
- 前层：头发遮挡、发丝、排线纹理。

目前并不是三维解剖学面部模型。CSS 参数只能调整部分相对尺寸，还缺少真实骨骼比例与自然的五官联动。

## 参数协议

```json
{"format":"portrait-engine-params","version":1,"parameters":{"faceWidth":100,"eyeSpacing":0,"noseWidth":100,"jaw":100,"graphite":65,"hatching":62,"hairVolume":100}}
```

`normalize()` 使用预定义数值范围，拒绝非数字，忽略未知字段。导入文件限制 1 MB。本地保存使用 `localStorage`；不上传文件，不调用 AI API，也不进行网络请求。

## 技术债务

1. 视觉仍然偏风格化，与专业写实铅笔素描相差明显。
2. 发丝、鼻梁、嘴唇和下颌的明暗过渡仍显得机械。
3. 参数还不足以生成十张外貌区别明显的独立人物。
4. 支持 JSON 参数导出和打印，不支持导出 PNG/SVG 成品。
5. 尚无全面多浏览器、真实设备及美术质量盲测。

## 后续架构原则

先提升艺术质量和结构化脸部参数，再按需求引入独立 SVG 绘制引擎。SVG 引擎不能冒充纯 CSS 绘制；AI 只能修改结构化参数，不得把 AI 生图悄悄替换到纯 CSS 画面。


## Research 002 / Plane and stroke renderer

The rendering pipeline keeps three concerns separate:

1. `src/parameters.mjs`: stable validated user parameters (v1 export remains
   compatible with legacy seven-control portraits).
2. `src/geometry.mjs`: explicit canvas-independent drawing-coordinate
   landmarks and derived CSS property values. These are *illustration*
   landmarks, not physiological model predictions.
3. `styles/portrait.css`, `styles/anatomy.css`, and `styles/graphite.css`:
   silhouette, anatomy planes, and region-specific pencil marks.

Each style is loaded in that order. The offline compiler embeds all four CSS
files (including `layout.css`) in exactly the same order. The renderer never
loads photos, AI image assets, SVG or Canvas drawing primitives.

The extra anatomy layers remain subordinate to the `.face` coordinates,
so changing face width scales these layers consistently. Ear and hair mass
are positioned relative to the outer face silhouette, not independently.
`deriveHeadLandmarks()` exposes visual design anchors for QA while the actual
paint remains CSS-only.

The nine-image browser matrix and JSON DOM measurements are **technical
invariants**. Human visual inspection remains necessary for proportion,
expression, gestural line quality, and perceived identity.

## Research 003 / landmarks vs render geometry

`styles/likeness.css` is loaded last and contains coherent overrides for face proportions, eyelid overlap, nose, lips, and side-part hair. `deriveHeadLandmarks()` now maps the actual unequal left and right eye group centers rather than a fictitious symmetric center. This is a 2D drawing approximation, not a physically correct anatomical rig. The offline bundler, browser QA in-memory loader, and main page must include every CSS layer; unit tests enforce the same drawing source.

## Research 004：独立视觉试验层

`styles/study004.css` 在 `likeness.css` 之后加载，集中存放候选面部形体与少量独立发丝的 CSS 声明。`index.html`、单文件构建和 Chromium QA 使用完全相同的样式顺序。浏览器试验脚本仅临时注入四种透明度配置来进行比较，生成图片不参与任何运行时绘制。

所有绘画图形仍是 HTML 元素、渐变、遮罩、阴影和边框，没有下载图片、内嵌 SVG、Canvas 或 AI 生图底图。CSS 的 2D 参数仍然是画面经验曲线，**不是**人体解剖模型或物理光线跟踪。
