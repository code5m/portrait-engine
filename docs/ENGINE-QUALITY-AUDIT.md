# 现有代码审计：通用生成能力与写实质量

基线：`main@611d53ce9b993f701ca103a635cd4e0bfec4dd6a`。这是代码和门禁审计，**不是**宣告完成独立艺术评价。

| ID | 观察到的实际缺口 | 影响 | 本轮处理 |
|---|---|---|---|
| AUD-01 | `src/app.mjs::apply()` 对整套 `deriveEngineStyle` 重复计算并设置一次，然后再次完整写入 | 浪费计算/重复 DOM style mutation，未来难以定位双写 | 去重，只保留一处 canonical style writer |
| AUD-02 | `test/asset-contract.test.mjs` 只扫描 `portrait.css` 的图片入口，其他 CSS 和 JS 可从旁路载图 | 违背唯一渲染媒介 | 跨所有 `styles/**` 和 `src/**` 静态禁令 + 浏览器运行时请求监控 |
| AUD-03 | `visual-study.yml` 的 PR 路径遗漏 `src/anatomy/**`、`src/expression/**` 等新模块 | 未来关键人脸代码可能跳过 Chromium | PR 触发路径覆盖所有 `src/**`, `styles/**`, `test/**`, `scripts/**` 与渲染相关工作流 |
| AUD-04 | `research013.yml` 固定 checkout 历史研究分支，授予 `contents:write` 并可能自动推送生成 HTML | PR 验证偏离 HEAD、写权限过大、分支分裂 | 工作流只读并使用当前 commit；单文件构建漂移会失败而非自动回写 |
| AUD-05 | R012/R013 单元只证实参数/像素变了；核心工程测试没有跨 3 身份×3 光照×5 表情截图覆盖 | 产生“矩阵覆盖”假象 | GitHub 增加真实 Chromium 45 场景/模式及身份/光照/表情不变量检查 |
| AUD-06 | 默认 V1 的 `apply()` 会自动挂载 `data-r006/r007/r008/r009`，虽然旧研究文档称每个实验都是 opt-in | 文档描述与实际产品基线不一致 | 不冒险改掉 V1 已发布外观；文档明示“当前默认 V1 复合渲染”，未来对照锁定真实默认截图 |
| AUD-07 | R012 首轮截图被明确拒绝，但 R013 仍只有工程差异测试，缺少独立观察者数据 | 不能将技术通过推断为更逼真 | 研究台账维持 `REJECTED_FIRST_VIEW` / `ART_UNVERIFIED`，人评与工程两条结果分开 |
| AUD-08 | `identity-model.mjs` 的 `age` 当前只是元数据，未进入 CSS 年龄形态或皮肤计算 | 不能声称会生成年龄相貌 | 留作视觉功能债务，后续必须增加可复现实验证据再转完成 |
| AUD-09 | `deriveIdentityFingerprint` 只编码部分 DNA 字段，不覆盖 brow/cheek.height 等全部身份细节 | fingerprint 唯一 ≠ 生物身份，也非加密校验 | 不在本轮破坏 JSON v2 协议；记录后续版本化修改与迁移测试 |
| AUD-10 | 人工评审尚无独立评分记录；零评分也会出现绿 CI | 不可自动产生真实性结论 | 质量状态单独建模；未经人工评审默认保持 `ART_UNVERIFIED` |
| AUD-11 | 缺少基于 PR base 的“默认绘制是否被偷偷改变”检查 | 未验证样式可能意外替换基线 | 同一 Chromium 进程渲染 PR base 和候选默认，中性脸 3×3 比较；未经审核改变则 fail |
| AUD-12 | 单文件 HTML 与 `index.html` 独立入口并存 | 确认两入口一致需要回归 | `npm run verify` 继续生成+比对；浏览器对生成的 standalone 做真实测试 |

## 不作为完成宣称的内容

1. 年龄感、肤质细节、全角度一致性与身份拟真都需要新增模型和质量数据；目前没有以实验验证。
2. R012/R013 已经合并到 main，只是为了保留可重复的研究实验；**不等于通过人像真实度验收**。
3. CSS 场景的不同哈希、像素差、变量差、检查点通过，只能证明“程序确实响应”，不能证明“人脸更真实”。
4. 代码规范/脚本无法自动验证匿名评分来自真实不同观察者，因此即使格式通过仍需明确的人类复核。
