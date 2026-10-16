# 素描研究尝试与失败记录

## S0 / attempt 1 / 2026-10-16 / FAILED

提交 `92830055f8ff98829cafdc408d3ca9216925089b`，Actions [38830228250](https://github.com/code5m/portrait-engine/actions/runs/38830228250)，job `116747165207`。

98 项 Node 测试通过；ICT 固定资产校验通过。Blender 4.0.2 输出九基本形体和无轮廓头部后，Freestyle 未关联 linestyle，触发 AttributeError。原命令没有 Python 异常退出码，错误退出为 0；后续评估因缺少 manifest 正确失败。修复显式创建/关联 linestyle 并使用 `--python-exit-code 1`。未降低原 MAE 门槛。

## S0 / attempt 2 / 2026-10-16 / CALIBRATION_COMPLETE, upload failed

测试源提交 `df72c4c965b5e9bfdeb8245e6a0d0ddb50df0cbf`，Actions [38830775186](https://github.com/code5m/portrait-engine/actions/runs/38830775186)，job `116748799000`。

真实日志：合并检出 `700cf3b00e8568fb67964f94bbee4aeb237f4cf0`；源码摘要 `eb4d846fd802071e6a7b13d0a4d6e566bccb13b078a48a811b9b661f59d75055`；参考/解析 MAE 0.2476–0.2879；CSS/解析 1.3488–1.5493；CSS/Blender 1.3153–1.5258；Freestyle 差 1.81161。九原人像基线、九 Blender 形体、九 CSS 形体、三三灰阶和两 ICT 参考帧实际生成。最后 artifact 配额不足，工作流整体 failure，不能称全绿。

## S0 / archive attempt / f6b9e4f / REJECTED

该提交曾将 S0 手工归档为 COMPLETE，但记录了错误的 39 位 ciCommit `d8b35e0e589ddc817516587f176585a2eece6d7aa2`、错误/过长源码摘要 `e61c9d443e6172f6e870631780e9ad712cb299c13bbb3d9d8df4619f6313680a29`。部分数值也不来自原日志：曾写参考/解析 0.2491–0.2529、CSS/Blender 1.3144–1.5125、Freestyle 1.50642，部分参考和三灰阶图的哈希不一致。这些旧值全部作废，不解释为正常跨平台波动。

阶段测试将该错误归档拦下；Actions 38831660015、38831660236、38831659988 失败。算法本身未因此获得失败或成功的新证据。

## S0 / provenance correction / 2026-10-16

逐项以原始 job 中的 S0_COMPLETION_JSON 为准替换证据与报告。保留以上错误来源，新增摘要/图像哈希格式、场景唯一性、计数和有限误差检查；不修改校准源码、不修改既定容差。纠正后需当前提交完整重跑，PR 未通过前不合并。

## 证据归档限制

Actions artifact 配额已满；不删除用户其他项目的 artifact，不声称上传成功。日志打印机器可读结果和紧凑参考/CSS 图；截图仅是评价证据，绝不成为人物运行时输入。
