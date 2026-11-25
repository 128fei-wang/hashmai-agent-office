# GitHub 开源合规整改报告

日期：2026-11-25 ｜ 仓库：`/Users/hashmai/roost-im/roost-ui-arch` ｜ 基线版本：v0.8.0

## 结论

**整改前**：该目录不是 git 仓库，`README / LICENSE / CONTRIBUTING / CODE_OF_CONDUCT / SECURITY` 全部缺失，
`.bak` 备份与个人视频抽帧混在源码目录里 —— 直接上传，GitHub 社区规范一项都不亮，且存在版权与凭据风险。

**整改后**：本地已是干净的 git 仓库（4 个提交 / 85 个文件 / 3.67 MB），
社区规范 12 项全部到位，`git clone` 到空目录后单测与校验全部通过，产物 sha 与基线一致。
**仍待你拍板 3 件事**：仓库名与归属、许可证（现 MIT）、公开还是私有。

## 一、新增文件（13 个）

| 文件 | 作用 | 字节 |
| --- | --- | --- |
| `README.md` | 项目定位、截图、三种打开方式、URL 参数、结构、文档索引、性能基线 | 见仓库 |
| `README.en.md` | 英文简介（给国际访问者与搜索引擎） | — |
| `LICENSE` | MIT 全文（2026 Hashmai） | — |
| `CONTRIBUTING.md` | 环境、构建顺序、提交前自测、代码约定、路线图 | — |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 中文版（含四级执行梯度） | — |
| `SECURITY.md` | 私密上报入口、受理范围表、可复现构建即防篡改闸门 | — |
| `CHANGELOG.md` | 0.1.0 → 0.8.0 逐版本，含 0.8.0 的 HUD 修复与实测数据 | — |
| `THIRD-PARTY-NOTICES.md` | PixiJS 8.6.6 MIT、素材自研声明、商标保留 | — |
| `package.json` | 名称/版本/sha 链/scripts（build、test、serve、bench）、无依赖 | — |
| `GITHUB-PUBLISH.md` | 推送命令、建库后 5 分钟设置清单、Release 与 Pages 步骤 | — |
| `.gitignore` | 备份、证据、个人素材、凭据、构建临时件全部兜底 | — |
| `.gitattributes` | LF 统一、二进制标注、产物 `linguist-generated` | — |
| `.editorconfig` | 缩进/编码/换行统一（py 4 空格，其余 2） | — |

`.github/` 下 6 个：

| 文件 | 作用 |
| --- | --- |
| `workflows/ci.yml` | 3 个 job：单测与校验、产物可复现、静态审计 |
| `ISSUE_TEMPLATE/bug_report.yml` | 结构化 Bug 模板（产物 sha / 渲染路径 / 环境 / 自检 JSON） |
| `ISSUE_TEMPLATE/feature_request.yml` | 结构化建议模板（先问「谁在什么场景」） |
| `ISSUE_TEMPLATE/config.yml` | 关闭空 issue，导流到私密安全入口与 Discussions |
| `PULL_REQUEST_TEMPLATE.md` | 验证输出 + 9 项检查清单（先改模板、禁手改产物） |
| `CODEOWNERS` | 全库由 `@hashmai` review |

## 二、清理动作（3 项）

1. **备份文件移出源码树**：7 个 `*.bak.*` / `*.truncated-*` 移到
   `/Users/hashmai/roost-im/_prep-github-archive-20261125/`，附 `MANIFEST.txt`，
   一个都没删、路径结构保持。
2. **个人视频抽帧出库**：`demo/shots/ref-a-wall-45s.png`（业主拍摄视频的截图）
   已 `git rm --cached` 并从后续提交排除 —— 本地文件仍在，但**不进开源仓库**，规避版权问题。
   `demo/shots/owner-video-1130/`（两张 1.2 MB 抽帧）已在 `.gitignore` 中。
3. **证据 JSON 不入库**：`d6-*.json`、`d5-*-bench.json`、`contract-selftest.json` 等
   属「跑出来的数据」而非源码，按 `.gitignore` 排除；结论已写进 `CHANGELOG.md` 与
   `D6-FPS-EVIDENCE-0170BE02.md`。

## 三、验证（全部实跑，非声明）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 状态机单测 | `node tools/test_sim.js` | **9/9 PASS**，rc=0 |
| 工位编号一致性 | `python3 tools/check_seat_ids.py --require-unified` | **seats=23 zones=8 fail=0**，rc=0 |
| 产物可复现 | `build_demo.py` 后比对 sha | 前后同为 `0170be02…`（78,058 B），**逐字节一致** |
| 单文件版可构建 | `python3 tools/build_single_file.py` | 755,120 B / `1c721b20…`，**外部引用残留 0** |
| JSON 可解析 | 遍历 `git ls-files '*.json'` | 全部通过 |
| 无网络请求 | `git grep` 自研代码 | 无 `fetch` / `XHR` / 外部地址 |
| 无凭据 | `git grep` 全库 | 无 token / 私钥 / `sk-` 模式 |
| 克隆可用 | `git clone` 到 `/tmp` 后重跑 | 84→85 文件、单测 9/9、sha 一致 |
| 大文件 | 最大 755 KB（单文件版），远低于 GitHub 100 MB 限制 | 通过 |
| 单文件隔离渲染（空目录） | 云主机 `/home/user/singlecheck/` 仅放 1 个 html | `renderer=webgl`、`renderers=1`、23 席、`grid=[53,24]`、`pixi_error=null`、首帧 `h-on=23`，截图 1600×1000 / 101,559 B |

> 已顺带修掉一处自查发现的误报：静态审计最初把内置 `demo/lib/pixi.min.js` 里
> 的错误提示当成外链，已把扫描范围收窄到自研文件（`office-demo*.html`、`sim.js`）。

## 四、仍需你决策（停点）

1. **许可证**：现 MIT。要改 Apache-2.0 / AGPL 的话，我改 3 处（`LICENSE`、`README.md`、`package.json`）。
2. **仓库名 / 归属组织**：现按 `hashmai/hashmai-agent-office` 写死 4 处链接；换名我全局替换。
3. **公开还是私有**：Public 才会点亮社区规范与安全公告入口。
4. 是否要我**代推到 GitHub**：本机未装 `gh`，且有 `GitHub-OAuth` 连接器——
   需要你一句「推」，我才建远端；否则执行 `GITHUB-PUBLISH.md` 第二节命令即可。

## 五、还没做（如实说明）

- **没有 push**：远端归属未定，且推送属外部写操作，需你确认。
- **CI 没在 GitHub 上跑过**：3 个 job 的每一步已在本地逐条等价复跑，但真实 Actions 环境
  （ubuntu + node 20 + python 3.12）尚未触发，首推后会看到第一份绿/红。
- **社区规范页面设置**（Description / Topics / Social preview / 分支保护）属网页设置项，
  代码推不上去，清单见 `GITHUB-PUBLISH.md` 第三节。
- **`gh` 未安装**，方式 B 需要先 `brew install gh`。
