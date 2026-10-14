# Portrait Engine · 可编程素描肖像实验

本项目从零使用 **HTML + CSS 绘制人物头部**。JavaScript 只负责交互和参数，不生成或加载头像图片。

**真实定位：目前是可运行的风格化素描实验，还没有达到专业写实素描水准。**

## 已实现功能

- 原创 CSS 头像：脸型、五官、头发、颈部、明暗、排线，均由 DOM 与 CSS 绘制。
- 七个可调参数：脸宽、眼距、鼻翼、下颌、明暗、排线、头发体积。
- 三个人物预设、实时预览、恢复默认、本地自动保存。
- 参数 JSON 导入/导出，包含输入校验和版本协议。
- 中文界面、响应式布局、键盘可操作的滑块。
- 独立的 `standalone.html`：无外部依赖，直接双击运行。
- Node 自动化测试及可选 Chromium 浏览器冒烟测试。

## 运行方式

最简单：直接双击 `standalone.html`。

开发模式：

```bash
npm run dev
```

然后打开 `http://localhost:4173`。

一键验证并重新生成单文件：

```bash
npm run verify
```

可选浏览器冒烟测试（安装 Python Playwright 与 Chromium 后）：

```bash
python3 test/browser-qa.py
```

## 目录说明

| 路径 | 用途 |
| --- | --- |
| `index.html` | 人物五官的 HTML 结构与操作界面 |
| `styles/anatomy.css` and `styles/graphite.css` | Research 002: facial planes, localized dry pencil marks and quieter hair mass |
| `styles/portrait.css` | 原创 CSS 画头部的核心代码 |
| `styles/layout.css` | 工作台布局、响应式与打印 |
| `src/parameters.mjs` | 参数契约、验证和 JSON 格式 |
| `src/i18n.mjs` | 中文文本 |
| `src/app.mjs` | 交互、状态保存与导入导出 |
| `scripts/build-standalone.py` | 生成独立 HTML |
| `test/` | 单元测试与浏览器冒烟测试 |
| `docs/` | 架构、验收和质量债务 |

## 原则

1. 不复制其他人的代码、图片或艺术作品。
2. 纯 CSS 人像不借用 SVG、Canvas、图片或第三方绘图库。
3. 不能把通过测试等同于艺术质量合格。
4. 未来如引入 SVG 渲染器，必须和纯 CSS 实验明确区分。

## 许可证

原创代码采用 MIT License。本项目不包含先前讨论的其他开源项目的代码与图片素材。

## Research 002: Anatomy and graphite marks

- Face structure now has independent CSS planes for brow ridge, eye socket,
  cheekbone, alar/nasal shadow, lower lip, chin and mandibular turn.
- Hair texture was reduced from mechanical bright stripes toward a dark mass
  with a few guided curved pencil strokes.
- The geometry module now exposes explicit drawing-coordinate landmarks.
  Nine face-width/lighting combinations can be rendered via:

```bash
python3 -m pip install playwright pillow
python3 -m playwright install chromium
python3 test/research-matrix.py
```

See `docs/RESEARCH-002.md` for the study log and honest visual limitations.
The portraits are still stylized; the nine render checks certify neither
human anatomical accuracy nor artistic realism.

## Research 003: face likeness and QA fidelity

Research 003 adds `styles/likeness.css`: intentionally asymmetric eye construction, a softer hairline, adjusted cheek/jaw volume, and reworked nostril/lip marks. `docs/RESEARCH-003.md` records browser-rendered evidence and the key limitation: this remains a stylized drawing, not professional graphite portrait realism. The nine-case real-browser matrix is archived as CI evidence, not used as a rendering asset.

## Research 004 — 清晰轮廓与写实性边界

本轮缩窄并打破规则的头发暗块，加强眼睑、鼻翼、嘴角的相互关系，将周期性网格纸纹改为微弱纸张颗粒。**从单张 CSS 艺术品向高写实素描迈进仍未完成。** 研究和四组发型试验、九组 Chromium 截图见 [研究记录](docs/RESEARCH-004.md)，可复现运行 `python3 test/hair-probe.py` 与 `python3 test/research-matrix.py`。

工程测试与艺术审核分开：浏览器渲染和无外部图像素材检查能自动化；美术写实度仍需要真人盲评，未通过、不得以 CI 绿灯冒充通过。

## Research 005：真正的对照研究（尚未获得人类评分）

不复制其他作品、不用图片、SVG 或 Canvas 渲染头像。为眼窝和嘴角提出两个**隔离的 CSS 绘画候选**，保留 Research 004 原版作为公平对照，不擅自把新版宣布为写实优胜者。

- 浏览器匿名对比：打开 [`study/005-blind.html`](study/005-blind.html)，三幅同参数人脸随机重排；每幅分别评估眼窝、嘴唇、整体可信度，并导出本地 JSON。该页面不上传评分。
- 自动化验证：`npm run verify`，然后运行 `python3 test/study005-visual.py`；实测浏览器绘制候选画面与 JSON 下载流程。
- 完整过程、反证标准和真实欠缺见 [`docs/RESEARCH-005.md`](docs/RESEARCH-005.md)。

**目前没有独立真人盲评数据，也没有证据能宣布哪幅更写实。**

## Research 006：统一体面光照（实验模式，未代替默认作品）

这轮研究让眉骨、眼窝、颧骨、鼻翼、下颌的明暗来自 **12 个面部体面法线与同一光源**，而非每个部位独立指定光影。它仍然是二维近似，不是真实三维人脸。

打开 `standalone.html?r006=volume` 查看纯 CSS 实验，使用 `standalone.html?r006=baseline` 作为对照。通过本地服务访问 [`study/006-compare.html`](study/006-compare.html) 可以同时查看 A/B。实验不修改用户已有存档，默认画面不变。

自动化：`npm run verify`、`python3 test/study006-visual.py`（9 种脸宽/光向组合 × 2 个版本，共 18 组截图）。真实限制和美术债务见 [`docs/RESEARCH-006.md`](docs/RESEARCH-006.md)。**仍无独立真人盲评，不能断言更写实。**

## Research 007：统一人脸局部结构坐标（仅实验，保持默认作品不变）

新增 `src/face-model.mjs` 中的 **FaceGeometry**：16 个面部局部位置节点，让眼窝/眼睛/眉毛、鼻翼/鼻侧以及颧骨/下颌共同读取一套结构坐标。绘画仍为原创 CSS，不使用图片、SVG、Canvas 或 AI 画图素材，也没有声明发明新语言。

通过浏览器打开 `standalone.html?r007=baseline`（固定坐标）和 `standalone.html?r007=structured`（共享锚点）比较；两边共用 Research 006 体面光源。若在仓库的 HTTP 服务下运行，可访问 [`study/007-compare.html`](study/007-compare.html) 对照以及 [`study/007-blind.html`](study/007-blind.html) 进行独立匿名评价。它们不会上传评分数据，也不会更改之前的人物存档。

复现 **54 张真实 CSS 浏览器渲染**与联动测试：`npm run verify && python3 test/study007-visual.py`。技术详情、反证标准、局限性与实验记录见 [`docs/RESEARCH-007.md`](docs/RESEARCH-007.md)；保留前六轮成果的架构原则见 [`docs/ADR-001-RESEARCH-CONTINUITY.md`](docs/ADR-001-RESEARCH-CONTINUITY.md)。目前仍是风格化肖像，独立真人艺术评分 **0**，状态 `ART_UNVERIFIED`。

## Research 008：共享结构生成局部明暗和铅笔纹理（可回退候选）

Research 007 的 16 个面部锚点，进一步定义一个连续的二维高斯基函数浮雕场。每个面部区域不再使用固定法线：`src/surface-field.mjs` 在共享位置上计算高度梯度，导出法线、明暗、鼻下投影位移与沿颊颌走向的排线角度。**这不是医学解剖模型、三维网格或真正的光线追踪。**

- `standalone.html?r008=legacy`：既有 R007 结构 + R006 固定法线（公平对照）。
- `standalone.html?r008=field`：同一结构、同一参数下，候选新明暗与结构排线。
- 本地服务中的 [`study/008-compare.html`](study/008-compare.html)：并排可交互检查两套画法。
- `npm run verify`：包含新增加的**打包 JavaScript 语法门禁**，防止各个源码文件都合法但拼接为单文件后重复声明而崩溃。
- `python3 test/study008-visual.py`：真实 Chromium 产生 36 张 A/B 对照图，检查光向、几何关系、遮挡位移与移动端。

默认肖像和所有旧角色 JSON v1 均保持不变；无图片、SVG、Canvas 或 AI 生图素材参与运行时绘制。完整试验、边界和视觉不足见 [`docs/RESEARCH-008.md`](docs/RESEARCH-008.md)。**美术写实度未经独立真人盲评，仍为 `ART_UNVERIFIED`，不能因为自动测试通过而宣称艺术进步。**


## Research 009 — 形体派生铅笔线（独立候选）

为正视角色已有的“塑料浮雕感”，新增 **同一 R008 浮雕场的纯 CSS 明暗 A/B**：`?r009=tonal` 是原有平滑阴影，`?r009=strokes` 使用共享法线决定 11 个局部区域的排线方向，光源决定线条可见度，同时适度降低模糊蒙层的强度。对比页：[study/009-compare.html](study/009-compare.html)，研究报告：[docs/RESEARCH-009.md](docs/RESEARCH-009.md)。

**只证明不同画法可以保留同一结构、动态响应光线；没有外部盲评，不能宣称哪张更像真人。** 默认人物、原 9 项参数和独立单文件 HTML 保持不变。
