# 人机双验证工作台与 API

最高原则：研究通用生成能力，以作品验证，以写实质量衡量。工作台不是效果图：它调用同一数值头部生成器和同一 HTML/CSS 绘制器。仓库保持私有，不代表已经部署了公开网站。

## 一键启动

```bash
bash workbench/start.sh
# 浏览器打开 http://127.0.0.1:4186
```

需要 Python 3.11+；脚本创建独立 `.venv-workbench`，安装锁定依赖与 Chromium。Ubuntu 缺少 venv 时安装 `python3-venv`。独立机器验证还需要 Blender：`sudo apt-get install blender`，或设置 `PORTRAIT_BLENDER` 为 Blender 可执行文件。Windows 双击 `workbench/start.cmd`。这些命令不自动公开你的服务或仓库。

## 不会编程也能操作

首次填写评审称呼，点击“准备参考模型”，选择人物参数与光照，点击“生成当前样本”。左图是实时 HTML/CSS；右图在点击“运行机器验证”之后由 Blender 独立生成。缺少依赖必须显示错误，不能假装验证通过。

填写五项评分，选择接受/修改/不接受，写问题；在“图上标注”输入意见后点击左图。勾选亲自查看，再保存。机器结果与人工评价分开保存，绑定源码摘要与固定样本散列。新算法或新样本不会自动继承旧评价。

阶段页读取仓库台账；历史页可重新打开样本、查看任务及导出评价。SQLite 保存于本地，重启不丢失已保存意见。修改/拒绝意见不会被机器 PASS 掩盖。单一用户或任意昵称不等于独立真实观察者；系统不自动签发 ART_PASS。

## API

`/api-guide` 是中文操作说明；`/api/v1/openapi` 是 OpenAPI 3.1。浏览器写操作使用 HttpOnly 会话和 `X-CSRF-Token`；程序可以使用已配置的 `Authorization: Bearer ...`。只允许 prepare/render/verify 三种任务，不接受任意 shell、URL、路径或可执行上传。

## 给其他人使用

本机运行只监听 127.0.0.1。共享时需你控制的服务器和 TLS 反向代理，设置随机 `PORTRAIT_TOKEN`（至少32字符）与 `PORTRAIT_PUBLIC_ORIGIN=https://你的域名`，再用 `--host 0.0.0.0` 启动。没有口令不允许对外绑定。受邀使用者只需浏览器和口令，不需要 GitHub 权限。

这是可信小组使用的研究工具，不是已经加固的多租户 SaaS。Dockerfile/compose 为部署模板，需在目标主机实际构建验证，不能把文件存在说成已部署。compose 默认仍只向主机127.0.0.1映射端口。口令不要写入仓库、日志或截图。

## 数据位置与边界

- `data/workbench/state.sqlite3`：任务、操作与评审；升级前备份整个数据目录。
- `data/workbench/vendor`：锁定的 MIT 数值模型，附许可与散列。
- `renders`：固定矢量区域描述；`machine`：机器验证；`captures/reference`：实际评价图片。
- 数据与虚拟环境已加入 `.gitignore`；删除数据目录会删除本地评价。

一个工作线程、最多8个排队任务。重启会将中断任务明确标为失败，要求重试。自动 UI 评分在独立临时数据库中标记 AUTOMATED_TEST，不进入真实用户数据。

S2 目前只研究中性正面头部表面与六个身份模式。不是医学骨骼/肌肉模型，也不包含完整皮肤、头发、自然表情或全局光照。与参考图数值接近不等于人物真实感已经通过。
