# Research 011：Face DNA Model 与程序化人物结构引擎

## 本轮目标

从手工 CSS 图层进入结构化人物模型。

过去版本已经证明浏览器可以绘制和参数化人脸，但五官仍然容易产生组件拼接感。

本轮开始建立：

```
Face DNA
   ↓
Geometry
   ↓
Volume
   ↓
Lighting
   ↓
Renderer
```

## 已完成

- 新增 `src/face-dna.mjs`
- 新增 `src/face-geometry.mjs`
- Face DNA 与渲染层分离
- 建立 skull / brow / orbit / nose / cheek / mouth / jaw 结构
- 增加 DNA 到二维绘制坐标的转换

## 当前限制

这不是医学级人体模型，也不是三维重建。

它只是一个可解释的二维人物结构抽象。

## 下一阶段

1. Volume Field
2. 统一光照解释
3. 多人物 DNA 实验
4. CSS Renderer 接入结构模型
5. 视觉回归测试

## 原则

- 不使用 AI 生成人脸替代绘制
- 不使用图片素材伪装
- 不把 CI 通过等同于艺术质量通过
