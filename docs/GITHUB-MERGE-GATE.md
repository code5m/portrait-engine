# GitHub 主线研发门禁：自动化与仓库权限的边界

适用：`code5m/portrait-engine`。宪章：[RESEARCH-CONSTITUTION.md](RESEARCH-CONSTITUTION.md)。

## 已在代码中设置的门禁

| 工作流 / Job | 验证对象 | 是否等于艺术真实 |
|---|---|---|
| `Verify / check` | 语法、研究规则、旧 JSON、可复现构建、全部 Node 断言 | 否 |
| `Visual study (headless Chromium) / visual` | 原有 001–010 与 V1 页面/实验浏览器验证；PR 的 `src/**`、`styles/**`、`test/**`、`scripts/**` 修改不会再漏触发 | 否 |
| `Research Governance — Universal CSS Portrait / Research Policy / Engine Contract` | 仅允许 CSS 原生画像、实验编号/开关、禁止单人硬编码、同步构建 | 否 |
| `Research Governance — Universal CSS Portrait / 3×3×5 Chromium / Default Visual Lock` | 当前默认与未拒绝实验的 45 场景/模式、R012 拒绝候选诊断九图、资源/JS 错误、光照/身份不变量、PR 与 base 的默认画像差异 | 否 |
| `R013 structural identity research` | 保留原研究 Chromium A/B 与测试，但移除自动 push 和写权限，检查当前 PR HEAD | 否 |

**区分两种强制性**：项目内检查脚本会在 GitHub Actions 中返回失败并标红，这属于**代码质量门禁**；只有在 GitHub 仓库设置了 required status checks / branch protection 或 ruleset 之后，GitHub 才会在服务器端拒绝任何绕过该检查的合并，这属于**平台级禁止合并**。两者不能混为一谈。

## 2026-10-16 连接权限核查

- `GET /repos/code5m/portrait-engine/rulesets` 返回 HTTP 403：`Upgrade to GitHub Pro or make this repository public to enable this feature.`（GitHub 对本私有仓库的规则集权益提示）。**不要为了开门禁而将项目设为公开仓库。**
- `GET /repos/code5m/portrait-engine/branches/main/protection` 返回 HTTP 403：`Resource not accessible by integration`。当前 GitHub 连接没有足够权限确认/更新主分支保护。
- 因此此代码变更**不能声称已在 GitHub 服务器端启用 required checks**。能够证明的是 CI 会运行上述工作流，失败会产生明确结果；管理员仍可能在权限允许时直接推送或绕过。

## 如仓库权限/套餐允许，由管理员一次性完成

1. GitHub Repository Settings → Rules / Branches 中创建保护 `main` 的规则，优先 **Require a pull request before merging**；禁止强制推送和删除。
2. 设置 **Require status checks to pass before merging**，选择 `Verify / check`、`Visual study (headless Chromium) / visual`、`Research Governance — Universal CSS Portrait / Research Policy / Engine Contract`、`Research Governance — Universal CSS Portrait / 3×3×5 Chromium / Default Visual Lock`（以 GitHub 实际显示的 job check 名称为准）。若将 `Visual study` 配置为必需，请确保工作流没有路径过滤导致文档类 PR 无 check，否则会永久等待；此时应取消路径过滤或使用单独、始终运行的汇总 check。
3. 保护先在测试 PR 上验证：人为提交非法 CSS `url(...)`、未经登记的 `r014` 实验、未经人工验证的默认画面修改，观察 PR 应红灯且不可合并。删除测试变更后回归绿灯。
4. 后续所有开发通过 GitHub PR 合并；不要以手动直接 push 绕过上述流程。

注意：工作流可能受 GitHub artifact 存储配额限制；图片附件上传失败不能把浏览器截图检查误判为艺术成功，也不能声称图像证据已经归档。主要浏览器门禁失败依旧会红灯。

## 人类观察者真实性的最终边界

`scripts/validate-human-evidence.mjs` 检查配对评分是否满足 2 批独立评审、至少 5 人/批、3 身份×3 光照×2 表情、7 维评分和预注册阈值；**它没有能力验证匿名观察者是否真实存在或独立**。需要实际盲测主持人/独立审阅确认，才可以允许候选推广到默认渲染。任何 AI 生成的评分或测试造数只用于检查解析器，不得成为本项目的 ART_PASS。
