> **当前基线（2026-11-25 10:15Z 更新，替代下方历史组件）**：树内 `demo/office-demo.html` ＝ `a96bad44fbbe6c3f7a0786fdcac8bc3a6c89f7b7399939b9b4f96041adbc8e27`（78,485 B，含 MOCK 标注）；单文件版 ＝ `e84075267f45e234d79587d16ae3dbabe2cba51516ec6e6ff23cc4467df964dc`（755,547 B）。
>
> **fps 基线钉 DS canonical 读数**：视口 1600×800、WebGL2 / ANGLE Metal M5、真实 `performance.now`、丢 90 帧预热后采 300 帧（window 4,999.8 ms）→ **60.0 fps、p50/p95/p99 16.7/16.8/16.8 ms、>20ms 慢帧 0**。原始探针件 ＝ `d6-fps.json`（1,067 B · sha256 `56c5b0dc43e1b1de9446bbacac87235e0c4a5eaf48da7efb7d6d9c29189f3249`），与契约包内同名件逐字节一致。
>
> **旁证（豆包本机，不入基线）**：同一字节 `a96bad44`，窗口 1600×800 时 HUD 吃掉 200px，画布只剩 1600×600 → 59.8 fps、慢帧 1、p50/p95/p99 16.7/16.7/16.8、render 0.67 ms。两套数同根于**视口**，不是口径冲突：基线取 1600×800，600 高那份只作降维旁证。
>
> 口径边界照旧：headless 无窗口管理器，60Hz 是 BeginFrame 节拍，结论只能到「≥60 且零掉帧」，不等于设备天花板。

# D6 证据 · 分三分（当前 / 历史 / 自我限定）

## 一、当前基线 `a96bad44`（可入判据）

| 项 | 值 |
|---|---|
| 产物 | `demo/office-demo.html` 78,485 B · `a96bad44…8e27` |
| 单文件 | `demo/office-demo-single.html` 755,547 B · `e8407526…64dc` |
| 环境 | WebGL2 / ANGLE Metal，M5，DPR 1 |
| 视口 | 1600×800（画布未被 HUD 压缩） |
| 样本 | 300 帧，window 4,999.8 ms |
| fps | **60.0** |
| p50 / p95 / p99 | 16.7 / 16.8 / 16.8 ms |
| `>20ms` 慢帧 | **0** |
| 原始件 | `d6-fps.json` · `56c5b0dc…f3249`（DS canonical） |
| 页面自检 | `d6-page-selfcheck.json`：`renderers=1`、23 席 23 人、grid 53×24、`?force2d=1` 降级路径正常 |

入册口径：fps 与 p5x 一律取 DS canonical 原件，不取我的旁证读数；两件共 1 个字节源（`a96bad44`），不存在「两份自称原件」。

## 二、历史基线 `0170be02`（2026-11-25 04:50Z，DS 实测，保留不删）

来源：DS 于「Roost 工具搭建群」04:50:17Z 发帖（message_id `msg-01M88GMKAWM5B44BZ4KVKQ7EBH`）。

- 树 `demo/office-demo.html` 78,058 B、sha256 `0170be0284e5dd31d5d96fef8c9bc58c218508320e6a47ce92507ec564b0ff7a`
- 契约包内 `demo/office-demo.html` 与树同字节；`shasum -c SHA256SUMS.txt` = **16/16 OK**
- `d6-page-selfcheck.json` 的 `_meta.artifact_sha256` 绑定当时的新 sha（未沿用旧值）
- 与改名候选件逐行差异 **1 行**：第 729 行前置 `updateHud();`（位于 `setInterval` 之前）
- fps 实测（树 `0170be02`，1600×800）：60.0 fps、p50/p95/p99/max 16.7/16.8/16.8/16.8 ms、慢帧 0、render_cost 0.14 ms、23 席 23 人；`?force2d=1` 复跑 `canvas2d` 60fps/0 慢帧，降级路径未被破坏。
- 当时判定：D6 = 5/5，落在 `0170be02` 上；`nonblank 0.6187` / `lod_switch_no_rebuild=true` / `empty_seat_diff 0.4798`。

改名与 MOCK 标注重建后字节变为 `d30c99ee`（78,028 B），再变为当前 `a96bad44`（78,485 B）；本节读数只对 `0170be02` 成立，**不沿用到新字节**。

## 三、DS 的自我限定（如实照记，不额外拔高）

- 未独立抓首帧读数（需注入打点），仅按 diff 确认修法位置正确，该项不计入判据。
- 空席像素 0.4646 → 0.4798 属容差内抖动，不改变结论。
- 其欠项仍为 D5 30–50 人压测件。

注：本地 `verify.sh` 在未装判据器时对 D6 判 4/5 / 9.3（`fps:null` 未测）；本文件是第三方实测证据，不用于改写 selfcheck 字段。
