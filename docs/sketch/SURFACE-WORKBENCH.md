# S5/S6 共用工作台操作

仍从同一个入口启动：`bash workbench/start.sh`，浏览器访问 `http://127.0.0.1:4173`，再进入同源路径 `/workbench/`。无需新建第二套工作台。升级前备份data目录；用户已有SQLite评价不迁移、不删除。

研究阶段下拉选择S5后，可选择原六身份、自定义六系数、左/正/右光、石墨/炭笔、无头发/短发纤维/侧梳纤维。S6选择预登记三组新参数与五种表情；不混用S5自定义系数。改变下拉不会偷偷改变当前固定样本，点击生成才产生新的样本和版本摘要。

首次追加模型准备会校验固定MIT源文件，可能需要下载。旧S2–S4仍使用原有冻结源和缓存。缺失依赖或哈希不符明确报错，不回退到假图。

视图有体积效果、结构、三灰阶、全部边缘控制、关闭全部材料、关闭头发。对照视图的评价不能用作候选接受。机器验证独立运行Cycles与真实Chromium，检查底层形体、光照、材料保护区、消融、参数效果和重现性。毛发和材料没有对应物理参考，不能把底层误差低称为头发真实。

真人观察已延期：可以只生成、运行机器验证、查看/导出结果，不需要勾选人工确认或填写评分。没有评审不会自动变成接受。S5/S6自动化UI验收甚至不写入虚构评分。

API与旧v1兼容，`/api/v1/openapi`提供运行时完整1.2.0模式：

```json
{"operation":"render","payload":{"stage":"S5","identity":"head-a","light":"left","material":"graphite","hair":"swept","expression":"neutral"}}
```

```json
{"operation":"render","payload":{"stage":"S6","identity":"novel-a","light":"front","expression":"smile","material":"charcoal","hair":"short"}}
```

按jobs接口查询完成后的renderId，再提交verify。浏览器写操作仍需会话+CSRF；配置的Bearer口令仍可供程序使用，不新增任意文件/URL/命令接口。

离线HTML包含原生CSS轮廓与数值描述、MIT来源声明，不贴PNG、SVG或Canvas。截图和独立参考仅是评价证据。头皮纤维不是完整三维毛发，石墨颗粒不是毛孔，新PCA组合不是新真人；ART_UNVERIFIED不因技术完成而变化。
