# D6 第三方复测 · 新基线 `0170be02`（2026-11-25 04:50Z，DS 实测）

来源：DS 于「Roost 工具搭建群」04:50:17Z 发帖（message_id `msg-01M88GMKAWM5B44BZ4KVKQ7EBH`）。

## 一致性核对（DS 本机）
- 树 `demo/office-demo.html` 78,058 B、sha256 `0170be0284e5dd31d5d96fef8c9bc58c218508320e6a47ce92507ec564b0ff7a`
- 契约包内 `demo/office-demo.html` 与树同字节；`shasum -c SHA256SUMS.txt` = **16/16 OK**
- `d6-page-selfcheck.json` 的 `_meta.artifact_sha256` 绑定新 sha（未沿用旧值）
- 与改名候选件逐行差异 **1 行**：第 729 行前置 `updateHud();`（位于 `setInterval` 之前）

## fps 实测（12:49 本地，树 0170BE02）
| 项 | 值 |
|---|---|
| 环境 | WebGL2 / ANGLE Metal M5 |
| 样本 | 300，真实时钟 4,999.8ms |
| fps | **60.0** |
| p50 / p95 / p99 / max | 16.7 / 16.8 / 16.8 / 16.8 ms |
| `>20ms` 慢帧 | **0** |
| render_cost | 0.14 ms |
| 视口 | 1600×800（与 v05 基线同视口，可比） |
| 席位 | 23 席 23 人 |

`?force2d=1` 复跑：`canvas2d-fallback` / `canvas2d`、23 席、60fps、0 慢帧 → 降级路径未被破坏。

## 判定
**D6 = 5/5，落在 `0170be02` 上。** `renderers=1` / `nonblank 0.6187` / `lod_switch_no_rebuild=true` / `empty_seat_diff 0.4798` 取自本机重取的 selfcheck（DS 核对了同 sha 且已入包）。

## DS 的自我限定（如实照记）
- 未独立抓首帧读数（需注入打点），仅按 diff 确认修法位置正确，该项不计入判据。
- 空席像素 0.4646 → 0.4798 属容差内抖动，不改变结论。
- 其欠项仍为 D5 30–50 人压测件。

注：本地 `verify.sh` 仍判 D6 4/5 / 9.3，因本机 `fps:null` 未测；本文件是第三方实测证据，不用于改写 selfcheck 字段。
