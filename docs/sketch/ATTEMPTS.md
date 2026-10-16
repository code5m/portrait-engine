# 素描研究尝试与失败记录

## S0 / attempt 1 / 2026-10-16 / FAILED

- 提交：`92830055f8ff98829cafdc408d3ca9216925089b`。
- GitHub Actions：[38830228250](https://github.com/code5m/portrait-engine/actions/runs/38830228250)，job `116747165207`。
- 98 项 Node 测试通过；固定版本的 ICT LICENSE 和中性网格散列校验通过。
- Blender 4.0.2 已输出九张基本形体及无轮廓的人头参考图，之后 Freestyle 失败：空场景的 line set 没有关联 linestyle，访问颜色得到 `AttributeError: 'NoneType' object has no attribute 'color'`。
- 原 Blender 命令没有配置 Python 异常退出码，进程退出为 0；后续总评估因缺少 `reference-manifest.json` 正确失败。因此不能据绿色单个命令步骤认定参考实验完成。
- Chromium 真实 file:// 校准已产出九场景；CSS 对解析灰度平均绝对误差 1.3488–1.5493（0–255 灰度，椭圆内部 q<0.92），当时只能作为阶段性技术结果，不是最终 S0 完成证据。
- 修复：显式创建并关联 Freestyle line style，设置 editor/可见边缘选择；CI Blender 加入 `--python-exit-code 1`。参考/解析 MAE<4 和 CSS/参考 MAE<6 原门槛保持不变。
- 当时结论：IN_PROGRESS，不允许标记 S0 COMPLETE，需重新实际渲染、比对并记录源码摘要。

## S0 / attempt 2 / 2026-10-16 / CALIBRATION_COMPLETE

- 测试源提交：`df72c4c965b5e9bfdeb8245e6a0d0ddb50df0cbf`。
- [Actions 38830775186](https://github.com/code5m/portrait-engine/actions/runs/38830775186)，job `116748799000`。CI 实际 PR 合并检出 SHA：`d8b35e0e589ddc817516587f176585a2eece6d7aa2`。
- Freestyle 完成；参考图与带线条参考图像素平均差 1.50642，证实选定线条实际产生，不能据此认定艺术质量更高。
- 九同场景校准通过全部原阈值：Blender/解析 MAE 0.2491–0.2529，CSS/解析 1.3488–1.5493，CSS/Blender 1.3144–1.5125。
- 复现九张旧 CSS 人像基线；生成九张 Blender 基本形体、九张 CSS 16 区域形体、三张三灰阶图、两张 ICT 参考图。全部图像用途分开，不能伪称新增真人。
- 证据快照：[S0.json](../../research/sketch/evidence/S0.json)。实现摘要 `e61c9d443e6172f6e870631780e9ad712cb299c13bbb3d9d8df4619f6313680a29`，阶段门禁检查代码变化是否导致证据过期。
- 阶段决策：S0 校准完成；S1 READY。带状灰阶、投影、反光、人脸结构迁移都留作后续，ART_UNVERIFIED。

## 证据归档限制

Actions artifact 配额已满，上传图片失败。评估在日志打印机器可读 completion JSON 和有标签的紧凑参考/CSS 图片，仓库保存实际数值及源码/图片散列；不声称完整图片附件已上传。任何压缩日志预览仅用于审查，不进入人物渲染链路。
