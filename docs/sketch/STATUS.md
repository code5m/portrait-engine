# 素描研究断点 / 从这里恢复

> 研究的是通用生成能力，人物作品是验证手段，写实质量是核心衡量标准。

- **已完成：S0 — COMPLETE（参考工具与形体明暗校准，不是人像写实完成）。**
- 证据：[S0.json](../../research/sketch/evidence/S0.json)；报告：[S0.md](S0.md)。
- 真实参考实验：[Actions 38830775186](https://github.com/code5m/portrait-engine/actions/runs/38830775186)，测试源分支提交 `df72c4c965b5e9bfdeb8245e6a0d0ddb50df0cbf`；报告另记录了实际 PR 合并检出 SHA。
- **当前待开始：S1 — READY**。S1 尚无完成实验，不得标记 COMPLETE；S2–S6 为 NOT_STARTED。
- **恢复后的首个操作：**读取 [S1.md](S1.md)，在相同几何/光向/相机下比较 16 个平色区域、16 个带内连续渐变区域、32 个平色区域的 CSS 结果；固定最多 32 区域/形体，记录全图/内部/边缘误差、DOM 和实际图像，再决定采用哪种表示。不要重新安装/重做已经完成的 S0。
- S1 后续才增加圆柱/楔形和受光面投影，分别验证形体阴影、投影、反光，不把常数 ambient 当成真实反光。
- 全局艺术状态：**ART_UNVERIFIED，独立真人观察者 0 位**。

## 每阶段完成必须持久记录

同一 PR 更新阶段报告、实际 CI 证据和源码摘要、`research/sketch/stages.json`、本断点。测试会阻止缺少报告/证据的 COMPLETE，并在 S0 实现与已记录证据不一致时失败。

S0 中一次 Freestyle 初始化失败及错误退出码缺陷已保留在 [ATTEMPTS.md](ATTEMPTS.md)；没有通过降低原有 MAE 容差放行。生产 `src/`、`styles/`、`standalone.html` 本阶段保持不变。
