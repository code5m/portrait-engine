# 验收门禁与未完成事项

## 已完成的自动化验证

- `npm run check`：JavaScript 源码语法检查。
- `npm test`：参数范围、预设、JSON 往返、错误输入、原型污染保护。
- `npm run build`：生成自包含 HTML。
- Chromium 浏览器冒烟测试：中文界面、九项滑块、实时变化、预设、重置、移动端无水平溢出。
- 绘画结构中没有图片、SVG、Canvas 节点。

## 未完成、不能冒充通过

- **专业级素描写实质量：未达标。**
- 十张具有自然身份差异的脸：未实现。
- PNG / SVG 成品图片导出：未实现。
- 跨 Chrome / Firefox / Safari / Edge 的完整实测：未完成。
- 面部结构真实解剖联动：未完成。
- CI 中人工艺术质量盲测：未建立。

## 下一阶段

优先改进素描比例、发丝排线、鼻梁和嘴唇的质感；之后开发真正的面部结构模型、精细编辑及多种导出。与直接 AI 生图的对比应以**可控性、稳定性和修改效率**进行实测，不凭主观热情判定商业价值。

## Research 001 quality status

- Nine interactive numeric controls, including mouth width and directional key light.
- A read-only construction guide overlay; view modes cannot modify stored portrait geometry.
- The derived landmark mapper is tested at narrow/wide silhouette and opposite lighting extremes.
- Legacy v1 seven-control JSON portraits still load with safe defaults for new controls.
- Offline build reproducibility is now checked on CI to detect source/bundle drift.
- Human/artist visual fidelity remains UNVERIFIED. Passing tests must not be described as realism achievement.


## Research 002 verification: objective versus aesthetic

- `npm run verify`: 17 tests passing (4 new pure-code tests covering
  anatomical layer presence, canonical landmarks, numeric/light invariants).
- `python3 test/browser-qa.py`: 9 sliders, structural modes and mobile
  responsiveness pass on real headless Chromium locally.
- `python3 test/research-matrix.py`: 9 CSS portrait screenshots and a
  single contact sheet for 80/100/120 percent face widths and -60/0/+60
  degree key-light positions. DOM bounds, eye ordering, light direction,
  pixel difference, browser errors, and mobile overflow checked.
- No image, SVG, Canvas or image URLs in the portrait rendering source.

**OPEN QUALITY DEBT:** The face is visibly stylized rather than a professional
pencil likeness. It still relies on a single identity topology and stylized
nasal/ocular geometry; the nine matrix images show controlled variations,
not nine independent identities. No artist blind review has been conducted.
The research issue remains open until that evidence exists.

## Research 003 additions

- [x] Intentional facial asymmetry and corrected eye-group landmark model.
- [x] Hairline and long rear-hair proportions adjusted after visual inspection.
- [x] Browser QA must inline all drawing CSS, preventing false passes with stale art.
- [x] 3 x 3 real Chromium rendering with structural and lighting pixel invariants.
- [ ] Independent art-quality blind review: still missing.
- [ ] Professional naturalistic graphite portrait: not achieved; no claims of photorealism.

## Research 004：工程门禁与艺术边界

- [x] 原始 CSS 绘画、四条独立发丝均不加载图片/SVG/Canvas/URL。
- [x] `styles/study004.css` 同步进入网页、离线 HTML、真实浏览器 QA。
- [x] 本地单元与契约测试：25 项通过。
- [x] 实际 Chromium 九宫格：9/9，通过五官边界、左右光照响应、手机横向溢出检查。
- [x] 四种发型透明度进行了真实浏览器对照，有可再现试验和量化记录。
- [ ] 独立艺术家盲评与专业铅笔素描质量验收：未完成。
- [ ] 不同人物身份、批量参数化人脸、照片级写实：未完成。
- [ ] GitHub 远端两项 CI 需以该提交的实际运行结果为准，不以本地测试替代。

**测试限制：** 深色像素比例变化只能表明明暗覆盖变化，不代表视觉真实程度得到独立认可；浏览器实现的鼻梁仍较几何化、眼睛仍有平面角色感。

## Research 005：独立艺术评审协议

- 已实现三方案（既有基线、眼窝结构、眼窝 + 口周结构）的匿名随机对照页；评分留在浏览器本地，导出的 JSON 包含映射以便研究者汇总。
- 新版不会静默替换既有默认角色。固定人物参数和光源才具备可比性。
- 执行 `python3 test/study005-visual.py` 与 GitHub Visual Study 工作流；自动化只验证浏览器画面和评审流程，**不得标记“独立盲评通过”**。
- 外部人类评分：**未收集**；专业写实素描：**未达标**。

## Research 006：统一光照模型，仍是候选

- [x] 独立 `src/volume.mjs`：12 个体面共用光向与法线，数学输入范围和左右侧光方向测试。
- [x] CSS-only 面部体面渲染；默认作品维持 `baseline`，`?r006=volume` 显式启用，不写入存档。
- [x] 旧 7/9 项参数协议兼容；独立单文件 HTML 同源构建。
- [x] 本地 Chromium 执行两种策略 × 九组参数渲染；真实 DOM、像素差、移动端和异常检查。
- [ ] **真人独立盲评：没有评分，不能宣布视觉改进。**
- [ ] **专业写实素描/一套参数生成多种身份：未完成。**
- [ ] **Chrome/Firefox/Safari 全兼容与严谨性能基准：未完成。**

详细记录见 `docs/RESEARCH-006.md`。GitHub CI 结果必须以远端实际检查为准。

## Research 007：共享 FaceGeometry 候选（不改变默认）

- [x] `src/face-model.mjs` 的 16 个人脸局部锚点、跨区域依赖与参数边界有单元测试；眼部、鼻部、颧骨、下颌多个 CSS 节点真实共享 CSS 变量。
- [x] R006 原光照算法与 R001–R006 所有源文件保持兼容；用户默认绘画与 7/9 参数 JSON 不变。
- [x] 本地 Chromium 54 帧 A/B 画面、下颌/脸宽极值、光照、移动端边界与匿名评分导出功能已自动验证。
- [x] `standalone.html` 采用原脚本单一事实源生成；QA 使用同一绘画源。
- [ ] 真正的独立真人盲评数据 **0 位**，艺术真实性 `ART_UNVERIFIED`。
- [ ] 严格跨设备性能分析、3D 解剖模型、独立身份生成和 PSL 语言仍**未实现**。

详细研究结论见 [RESEARCH-007](RESEARCH-007.md)。代码 CI 绿灯只能表示工程验证通过，不能代替美术验收。

## Research 008：结构生成光影、软遮挡和排线

- [x] 候选使用 R007 原生锚点构造连续 2.5D 高度场，R006 共享光向控制 12 区阴影；改变下颌/鼻宽/眼距有实际数值变化；面部水平缩放也进入局部法线梯度，避免只压缩画面却不更新光照。
- [x] 鼻下投影方向随光向反转，颊颌排线角度随颊骨—下颌切线变化，渲染器仍严格为 HTML + CSS。
- [x] 独立 opt-in A/B 方案，旧 7/9 参数格式与默认作品不变。
- [x] 构建后的独立 JS 再做语法检查；修正研究时发现的单文件模块顶层重名导致的浏览器白屏问题。
- [x] 本地 `npm run verify` 与 Chromium 36 帧渲染 + 手机裁切检查（具体执行日志见研究文档）；远端 CI 需针对本次提交单独验证。
- [ ] **外部真实艺术盲评**：仍为 `ART_UNVERIFIED`。
- [ ] 真实 3D 解剖、自然发丝、十个独立人物身份、实际跨设备光栅性能测试：未实现。

工程渲染中的像素差、阴影方向、节点数量**不能代表绘画质量**。即使美术候选更暗、更复杂，也不自动升级为默认画面。


## Research 009：结构等值线排线候选

- [x] 同一 R008 面部结构下 `?r009=tonal` / `?r009=strokes` 可独立比较，不改变默认作品。
- [x] 11 个局部笔触区域的方向由浮雕场法线计算，排线密度由同一光源和铅笔参数计算；计算模块不操作图片像素。
- [x] `test/stroke-field.test.mjs` 对角度界限、受光反转、零排线值和默认旧协议做回归。
- [ ] `test/study009-visual.py` 浏览器帧检查 / `GitHub Visual Study`：以当次实际运行状态为准。
- [ ] 真人盲评仍为 0。较密线条可能显得机械；**工程通过不是 ART_PASS**。
