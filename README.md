# Portrait Engine · 可编程素描肖像实验

本项目从零使用 **HTML + CSS 绘制人物头部**。JavaScript 只负责交互和参数，不生成或加载头像图片。

**真实定位：目前是可运行的风格化素描实验，还没有达到专业写实素描水准。**

## 已实现功能

- 原创 CSS 头像：脸型、五官、头发、颈部、明暗、排线，均由 DOM 与 CSS 绘制。
- 七个可调参数：脸宽、眼距、鼻翼、下颌、明暗、排线、头发体积。
- 三个人物预设、实时预览、恢复默认、本地自动保存。
- 参数 JSON 导入/导出，包含输入校验和版本协议。
- 中文界面、响应式布局、键盘可操作的滑块。
- 独立的 `standalone.html`：无外部依赖，直接双击运行。
- Node 自动化测试及可选 Chromium 浏览器冒烟测试。

## 运行方式

最简单：直接双击 `standalone.html`。

开发模式：

```bash
npm run dev
```

然后打开 `http://localhost:4173`。

一键验证并重新生成单文件：

```bash
npm run verify
```

可选浏览器冒烟测试（安装 Python Playwright 与 Chromium 后）：

```bash
python3 test/browser-qa.py
```

## 目录说明

| 路径 | 用途 |
| --- | --- |
| `index.html` | 人物五官的 HTML 结构与操作界面 |
| `styles/portrait.css` | 原创 CSS 画头部的核心代码 |
| `styles/layout.css` | 工作台布局、响应式与打印 |
| `src/parameters.mjs` | 参数契约、验证和 JSON 格式 |
| `src/i18n.mjs` | 中文文本 |
| `src/app.mjs` | 交互、状态保存与导入导出 |
| `scripts/build-standalone.py` | 生成独立 HTML |
| `test/` | 单元测试与浏览器冒烟测试 |
| `docs/` | 架构、验收和质量债务 |

## 原则

1. 不复制其他人的代码、图片或艺术作品。
2. 纯 CSS 人像不借用 SVG、Canvas、图片或第三方绘图库。
3. 不能把通过测试等同于艺术质量合格。
4. 未来如引入 SVG 渲染器，必须和纯 CSS 实验明确区分。

## 许可证

原创代码采用 MIT License。本项目不包含先前讨论的其他开源项目的代码与图片素材。