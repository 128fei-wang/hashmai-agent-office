# 参与贡献（Contributing）

感谢你愿意花时间。这个项目是一个**单页前端 + 纯逻辑状态机**的小工程，
比一般的开源项目更容易参与——改动都能在一台普通笔记本上跑通、看完。

## 环境要求

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.10+ | 构建脚本、校验脚本 |
| Node | 18+ | 状态机单测、压测 |
| 浏览器 | 近两年的 Chrome / Edge / Safari / Firefox | 打开 `demo/office-demo.html` |

无 npm 依赖、无 pip 依赖，不需要 `npm install`。

## 本地跑起来

```bash
python3 -m http.server 8080
# 打开 http://localhost:8080/demo/office-demo.html
```

改完源码后必须重新构建（脚本有顺序依赖）：

```bash
python3 tools/build_office.py
python3 tools/build_seatmodel.py
python3 tools/build_tiles.py
python3 tools/build_sprites.py
python3 tools/build_demo.py
python3 tools/build_single_file.py
```

> **请注意分工**：`demo/office-demo.html` 与 `demo/office-demo-single.html` 是**产物**，
> 不要手改。要改样式、改布局、改埋点，请改 `demo/office-demo.template.html`，
> 再跑 `build_demo.py`。手改产物会在下一次构建时被覆盖，CI 也会直接失败。

## 提交前必须自测

```bash
node tools/test_sim.js                              # 期望 9/9 PASS
python3 tools/check_seat_ids.py --require-unified   # 期望 SUMMARY seats=23 zones=8 fail=0
```

两项都必须 rc=0 才能提 PR。CI 会再跑一遍，并额外校验
「从模板重建出的 `demo/office-demo.html` 与仓库内提交的产物逐字节一致」。
如果你改了模板却忘记重新构建，CI 会在这一步失败并告诉你 sha 对不上。

## 提 Issue

- **Bug**：用 Bug Report 模板，附上浏览器 / 系统 / 是否 WebGL 降级（`?force2d=1` 是否复现）、
  复现步骤、期望 vs 实际，最好带截图。
- **功能建议**：用 Feature Request 模板，说明「谁在什么场景下会用到」，而不是只写「加个 X」。
- **安全问题**：**不要开公开 issue**，按 [SECURITY.md](SECURITY.md) 私密上报。

## 提 PR

1. 从 `main` 切分支：`feat/...`、`fix/...`、`docs/...`。
2. 一个 PR 只做一件事；格式化、重命名这类纯噪声改动单独提。
3. 提交信息用祈使句短句，能说清「改了什么」和「为什么」：
   `fix(hud): 首帧先刷一次 updateHud，避免前 300ms 显示在岗 0`
4. PR 描述里写清：改了什么、怎么验证的（贴自测输出）、有没有影响既有产物 sha。
5. 涉及渲染或布局的改动，请附一张改动前后的截图对比。

## 代码约定

- **HTML / JS**：2 空格缩进；变量名用 camelCase；常量大写；不引入新的运行时依赖
  （PixiJS 已内置在 `demo/lib/`，需要换版本请单独提 PR 并说明理由）。
- **Python**：4 空格缩进，函数加类型注解，脚本入口保持「可重复执行、失败即非 0 退出」。
- **不要引入网络请求**：面板必须能在完全离线的机器上打开。
- **不要提交凭据**：`state.json`、`.env`、token、内网地址一律不入库（`.gitignore` 已兜底）。
- **数据要可解释**：任何统计口径的改动，请在 PR 里写清公式与样例，不接受「看起来更准」。

## 文档

- 面向使用者的改动 → 更新 `README.md`
- 架构 / 渲染分层 → 更新 `ROOST-UI-ARCH-01.md`
- 地图分区 / 席位编号 → 更新 `OFFICE-MAP-01.md`、`SEAT-ID-MAP.md`
- 版本演进 → 追加 `CHANGELOG.md`（`Unreleased` 段）

## 行为准则

参与本项目即表示你同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
维护者会对恶意刷屏、人身攻击、政治与歧视性言论直接关闭讨论，不解释。

## 路线图（欢迎认领）

- [ ] 接真实事件流（store）替换模拟数据
- [ ] 点席位查看该 agent 的当前任务与历史
- [ ] 30 秒回放（拖动时间轴重放一段动线）
- [ ] 30 / 50 agent 规模下的渲染压测与 LOD 策略调优
- [ ] 深色 / 浅色双主题
- [ ] i18n（中 / 英）
