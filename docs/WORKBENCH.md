# 人机双验证工作台与 API

最高原则：研究通用生成能力，以作品验证，以写实质量衡量。工作台调用同一数值头部生成器与 HTML/CSS 绘制器。仓库保持私有，不代表已部署公开网站。

## 从源码启动

```bash
bash workbench/start.sh
# 浏览器打开 http://127.0.0.1:4186
```

需要 Python 3.11+；脚本创建独立 `.venv-workbench`，安装锁定依赖与 Chromium。Ubuntu 缺少 venv 时安装 `python3-venv`。独立机器验证需要 Blender：`sudo apt-get install blender`，或设置 `PORTRAIT_BLENDER`。Windows 双击 `workbench/start.cmd`。不会自动公开仓库或服务。

## 不会编程也能操作

首次填写评审称呼，点击“准备参考模型”。选择研究阶段、人物参数和光照，点击“生成当前样本”。首次几何编译可能需要数分钟；状态会显示执行进度，不用反复提交。完全相同的源码与参数可复用已校验的数值结果，但不会复用过期验证。

- **S2：头部结构。** 冻结的原始结构与法线明暗参考。
- **S3：大明暗与光源遮挡。** 明确的直接受光、遮挡与半球补光近似。切换三大灰阶查看整体关系。
- **S4：边缘层次。** 同一 S3 体积上选择遮挡/轮廓/有依据的转折；可以切换“全部结构硬边”对照，不把对照的评价混进候选接受结果。

这些是可操作的实验模式；是否完成阶段以“阶段档案”及对应证据为准，**有模式不代表阶段通过**。更换下次生成阶段不会偷偷替换当前固定样本。图像右侧仅在点击“运行机器验证”后由 Blender 独立生成，缺依赖明确报错。

填写五项评分，选择接受/修改/不接受；在图上标注框输入意见后点左图位置，勾选亲自查看并保存。记录绑定阶段、源码摘要、固定样本散列与观察方式。结构或三灰阶的接受不能自动当作完整体积效果已接受；任何未解决的修改/拒绝不会被一次接受覆盖。机器与人工分别保存，永不自动签发 ART_PASS。

## API 与示例

`/api-guide`：中文使用说明；`/api/v1/openapi`：OpenAPI 3.1。
浏览器写操作使用 HttpOnly 会话和 `X-CSRF-Token`；程序可使用已配置的 `Authorization: Bearer ...`。

```json
{"operation":"render","payload":{"stage":"S4","identity":"head-a","light":"left"}}
```

向 `/api/v1/jobs` 提交，取得 jobId 后查询 `/api/v1/jobs/{id}`；成功返回 renderId。再提交 `{"operation":"verify","payload":{"renderId":"返回的id"}}` 运行独立验证。stage 默认 S2，旧调用保持兼容。只允许 prepare/render/verify，禁止任意 shell、URL、路径与可执行上传。机器结果不能由客户端伪造。

## 共享和数据

默认仅监听127.0.0.1。受邀共享需要你控制的服务器、TLS反向代理、随机 `PORTRAIT_TOKEN` 至少32字符和 `PORTRAIT_PUBLIC_ORIGIN=https://你的域名`；然后明确 `--host 0.0.0.0`。无口令不能对外绑定。可信小组只需浏览器和口令；不是已加固多租户SaaS。Docker/compose只是部署模板，需目标机器实测。

SQLite：`data/workbench/state.sqlite3`；数值模型vendor、固定描述renders、机器报告machine、参考reference，以及S3/S4的studies。升级前备份整个data目录。数据和虚拟环境均在.gitignore中。删除data会删除评价，不能把临时测试数据当真人记录。

单工作线程、最多8个排队任务。重启把中断任务显式标为失败，不伪称完成；可重试。自动化评分使用独立临时库并标记AUTOMATED_TEST，不进入真实用户意见。

## 真实边界

Python API进行数值几何计算，JS/CSS在浏览器绘制；尚不是完全浏览器端几何计算。S2–S4目前限定中性正面头部表面，不是医学骨骼肌肉模型。没有毛孔、复杂发丝、自然表情或全角度能力。S3半球补光不是完整GI，S4的局部边缘策略是否更像真实素描必须由实际观察判断。技术通过不能替代你的评价和独立盲评。
