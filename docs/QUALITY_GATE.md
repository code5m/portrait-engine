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
