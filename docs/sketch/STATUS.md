# 素描研究断点（GitHub 主源）
最高原则：**研究的是通用生成能力，人物作品是验证手段，写实质量是核心衡量标准。**

## 当前阶段

| 阶段 | 工程状态 | 证据 |
|---|---|---|
| S0–S4 | COMPLETE（限定技术实验） | 先前各阶段 `docs/sketch/` 与 `research/sketch/evidence/`；本轮旧阶段回归成功 |
| S5 | **COMPLETE（限定技术实验）** | `docs/sketch/S5.md`、`research/sketch/evidence/S5.json`，18/18 |
| S6 | **COMPLETE（限定技术实验）** | `docs/sketch/S6.md`、`research/sketch/evidence/S6.json`，45/45 |

目前台账的 `currentStage=S6` 表示**最后一个已结题的工程阶段**，不表示已通过写实人物艺术验收。权威状态始终以 `research/sketch/stages.json` 与原始证据为准。

## 本轮完整完成证据

- 冻结源提交：`029bd05ab357e9e47e562fb88ac5e41854047021`
- CI 运行：[38912892498](https://github.com/code5m/portrait-engine/actions/runs/38912892498) — 六个 S5 case、十五个 S6 case、真实 API/UI 与全部 63 画面、独立 Cycles 参考、原始记录收集、聚合检查 **全部 PASS**。
- 原始证据归档：`evidence/sketch-s5-s6-38912892498-1`，提交 `20af507e2f688064997843c259201dfe3c7b4479`，文件路径 `research/sketch/evidence/raw-surface/38912892498/`。含 PNG 与 JSON 共 **787 文件 / 20,574,045 字节**；`manifest.json` 带 SHA-256。
- 旧失败保留：运行 38883924059 全部场景通过但证据 Git tree 单次提交 422；归档改分批原子合成并经真实 CI 通过；初期其他失败亦保留历史记录。
- 真人观察：**DEFERRED_BY_OWNER；0 人；ART_UNVERIFIED**；不能声称真人写实已经达标，不能自动晋升默认渲染器。

## 下一步，无须重新讨论既定目标

1. 使用工作台与 S0–S6 全部可复现素材建立独立的**真实人物素描质量基准**：头部结构、体积、眼神与表情、软边、排线和发束的真写实诊断。数值越接近 Cycles 无纹理参考不等于美术质量越好。
2. 使用**没有参与本次调试的新真实身份资料**及更多视角验证通用生成力；继续保留 HTML+CSS 绘制、JS 计算，禁止 Canvas/SVG/图片/WebGL 替代人物。
3. 继续自动化工程与失败样本收集；待用户方便时启用工作台的人机双验证与独立匿名评价。此项不阻塞探索，但阻塞艺术 PASS 与默认晋升。

所有阶段完成或新假设必须同步更新报告、证据、台账、本断点；不得把聊天消息当仓库唯一记录。
