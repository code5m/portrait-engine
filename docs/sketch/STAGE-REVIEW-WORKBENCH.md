# S0–S6 阶段证据与人工审核工作台

统一入口：`npm run dev` 或 `bash workbench/start.sh`，打开 `http://127.0.0.1:4173`，由主页导航进入 `/workbench/`，登录后选择「阶段档案」。

## 已实施
- S0–S6 七张阶段卡片，展示阶段状态、技术场景数量和是否有可追溯原始图片。
- 展开阶段后可切换真实场景，逐项看数值、归档原始 PNG、独立参考和消融图；查看对应 CI 与阶段报告。
- 不允许用户输入任意图片路径。图片只能由服务器根据登记场景、manifest 和 SHA-256 提供；文件损坏时拒绝展示。
- 审核表单必须由真人选定当前图片、录入五项质量维度、选择接受/修改/拒绝、明确勾选实看声明；提交绑定阶段证据 SHA-256 和场景。
- 人工审核写入独立的 `stage_reviews` SQLite 表，不修改 `stages.json`、`research/sketch/evidence/` 的技术研究状态，也不允许用户自己给 ART_PASS。
- 仅登录会话或被授权的 Bearer token 可读取 API；更改评审必须通过现有 CSRF/会话保护，测试模式不产生真实人工证据。

## 原始证据历史边界
- S3/S4 使用归档 run `38866567327`，当前选择性展示 S3、S4、硬边/三灰阶和独立 Cycles 对照。
- S5/S6 使用归档 run `38912892498`，当前选择性展示本次场景的原生素描、独立参考、材料和发型消融。
- S0–S2 原有测量/报告与 hash 可查看，但完整原始 PNG 没有可靠归档；不得用以后生成的图片冒充当年的同版本原图。原图未归档时，阶段审核按钮禁用（仍可读技术结论）。
- 阶段技术 COMPLETE 是冻结协议机器实验完成，不代表真人写实通过。艺术状态仍然是 `ART_UNVERIFIED`。

## 新增 API
- `GET /api/v1/stage-results`：七阶段摘要。
- `GET /api/v1/stage-results/S5`：该阶段的测量场景、图像与已存人类意见。
- `GET /api/v1/stage-results/S5/images/head-a-neutral-left/0`：已归档且 hash 校验的 PNG。
- `POST /api/v1/stage-reviews`：现场人工评价，字段 `stage,sceneId,revision,verdict,scores,note,humanConfirmed`。

## 后续补齐策略
用**原始仓库可验证产物**恢复 S0/S1/S2 的预览图，核实源 SHA、运行 ID 和文件 digest 后再纳入图库；无法恢复则保留缺失提示，并创建明确标识的新基准复验，不要伪造旧实验。
