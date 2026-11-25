# 第三方组件与素材说明（Third-Party Notices）

本仓库自身代码以 [MIT](LICENSE) 发布。以下是随仓库分发或参考的第三方内容，各自的授权以其原始声明为准。

## 运行时依赖

### PixiJS 8.6.6

- 位置：`demo/lib/pixi.min.js`（内联进 `demo/office-demo-single.html`）
- 授权：**MIT License**
- 版权：Copyright (c) 2013-2025 Mat Groves / PixiJS contributors
- 上游：https://github.com/pixijs/pixijs
- 说明：内置而非走 CDN，是为了让面板在**完全离线**的机器上也能打开。
  升级版本请单独提 PR，并同步更新本文件与 `demo/lib/` 下的产物。

## 设计参考（非代码复用）

- 像素办公室的**视觉骨架思路**参考了开源社区流行的 pixel-office / pixel-agents 类项目。
  本仓库的地图数据、渲染层、状态机、寻路与构建脚本均为本项目自研，未复制其代码。
- 如需追溯具体参考对象与授权，请在 issue 中说明，我们会补齐链接与授权原文。

## 素材

| 文件 | 来源 | 授权 |
| --- | --- | --- |
| `assets/office-tileset.png` | `tools/build_tiles.py` 程序化生成 | 随本项目 MIT |
| `assets/agents.png` | `tools/build_sprites.py` 程序化生成 | 随本项目 MIT |
| `assets/office-map.tmj` / `office-map-preview.png` | `tools/build_office.py` 程序化生成 | 随本项目 MIT |
| `demo/shots/*.png` | 本项目渲染截图 | 随本项目 MIT |

> 仓库**不包含**任何来自第三方视频、影视、游戏或商业素材的抽帧或截图。
> 个人拍摄的参考视频抽帧仅作本地比对，已在 `.gitignore` 中排除，不入库。

## 字体

面板不打包任何字体文件，使用系统字体栈
（`-apple-system, "PingFang SC", "Hiragino Sans GB", sans-serif`），因此不涉及字体授权分发问题。

## 商标

「哈希麦 / Hashmai」名称与标识为商标保留项，**不在 MIT 授权范围内**。
你可以自由使用、修改、分发代码，但不得以本项目名义或使用其标识进行商业背书。
