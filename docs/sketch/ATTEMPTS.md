# 素描研究尝试与失败记录

## S0 / attempt 1 / 2026-10-16

- 提交：`92830055f8ff98829cafdc408d3ca9216925089b`。
- GitHub Actions：[38830228250](https://github.com/code5m/portrait-engine/actions/runs/38830228250)，job `116747165207`。
- 98 项 Node 测试通过；固定版本的 ICT LICENSE 和中性网格散列校验通过。
- Blender 4.0.2 已输出九张基本形体及无轮廓的人头参考图，之后 Freestyle 失败：空场景的 line set 没有关联 linestyle，访问颜色得到 `AttributeError: 'NoneType' object has no attribute 'color'`。
- 原 Blender 命令没有配置 Python 异常退出码，进程退出为 0；后续总评估因缺少 `reference-manifest.json` 正确失败。因此不能据绿色的单个命令步骤认定参考实验完成。
- Chromium 的真实 file:// 校准已产出九场景；CSS 对解析灰度平均绝对误差 1.3488–1.5493（0–255 灰度，椭圆内部 q<0.92），仅是阶段性技术结果，不是最终 S0 完成证据。
- 修复：显式创建并关联 Freestyle line style，设置 editor/可见边缘选择；CI 运行 Blender 时加入 `--python-exit-code 1`。参考/解析 MAE<4 和 CSS/参考 MAE<6 的原门槛保持不变。
- 结论：**IN_PROGRESS，不允许标记 S0 COMPLETE**，需重新实际渲染、比对并记录源码摘要。

## 证据归档限制

Actions artifact 存储配额已满，上传图片失败。最终评估成功时会同时在日志打印机器可读 completion JSON 和有标签的真实参考/CSS 图片；它们用于审查，不是产品渲染输入。只有从真实运行记录取得的结果才可以写入阶段完成证据。
