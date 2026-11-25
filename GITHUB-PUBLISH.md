# 发布到 GitHub：清单与命令（GITHUB-PUBLISH）

本仓库已经按 GitHub 社区规范整理完毕，**本地是干净的 git 仓库**（3 个提交、84 个文件、无凭据、无大文件）。
下面是把它推到 GitHub 并点满社区规范的步骤。

---

## 一、需要你拍板的 3 件事（停点）

| # | 事项 | 现状 / 建议 | 影响 |
| --- | --- | --- | --- |
| 1 | **仓库名与归属** | 建议 `hashmai/hashmai-agent-office`（与 `package.json`、README 中的链接一致） | 改了要全局替换 4 处链接 |
| 2 | **许可证** | 已落地 **Apache-2.0**（含专利授权，授权范围是 MIT 的超集；发布后不可追溯更换，故发布前定稿） | 影响他人能否商用、是否必须回馈源码 |
| 3 | **公开还是私有** | 开源 = Public（社区规范文件才有意义）；先 Private 试推也行 | Public 后即被索引，撤回成本高 |

> 未拍板前我不会创建远端、不会 push。仓库只在你本机。

## 二、推送（二选一）

### 方式 A：网页手动（最稳，不需要装 gh）

1. GitHub 上 **New repository** → 名称 `hashmai-agent-office` → **不要**勾选 "Add a README/.gitignore/license"（否则会与本地冲突）→ 建好后复制仓库地址。
2. 本机执行：

```bash
cd /Users/hashmai/roost-im/roost-ui-arch
git remote add origin https://github.com/hashmai/hashmai-agent-office.git
git push -u origin main
```

### 方式 B：gh CLI（本机当前未安装）

```bash
brew install gh
gh auth login                     # 走浏览器授权
cd /Users/hashmai/roost-im/roost-ui-arch
gh repo create hashmai-agent-office --public --source=. --remote=origin --push \
  --description "像素风多 agent 办公室监控面板：老板→运营中心→各部门（≤3 工位），PixiJS 8 + 零构建依赖"
```

## 三、建库后 5 分钟把社区规范点满

在仓库 **Settings** 里逐项设置（这些是网页设置，代码推不上去）：

- [ ] **Description**（一句话，同上）
- [ ] **Topics**：`multi-agent` `pixijs` `dashboard` `visualization` `pixel-art` `agents`
- [ ] **Website**：可留空，或指向 Pages 演示地址
- [ ] **Features**：勾选 *Issues*、*Discussions*；*Wiki* 可选
- [ ] **Social preview**：上传 `demo/shots/v08-rename-hud.png`
- [ ] **Branches → main 保护**：Require PR + Require status checks（选 `CI / 单测与校验`、`CI / 产物可复现`）
- [ ] **Security → Advisories**：开启 Private vulnerability reporting（`SECURITY.md` 里已指向该入口）
- [ ] **Code security**：开启 Dependabot alerts（本项目无 npm 依赖，只监控 Actions）

## 四、首版发布（Release）

```bash
cd /Users/hashmai/roost-im/roost-ui-arch
git tag -a v0.8.0 -m "v0.8.0 哈希麦多agent办公室：改名 + 首帧 HUD 修复"
git push origin v0.8.0
```

然后在 **Releases → Draft a new release** 选 `v0.8.0`，把 `CHANGELOG.md` 的 `[0.8.0]` 段贴进正文，
附件上传 `demo/office-demo-single.html`（单文件验收版，双击即开）。

## 五、可选：Pages 在线演示

Settings → Pages → Source 选 `main` / `/ (root)` → 访问
`https://hashmai.github.io/hashmai-agent-office/demo/office-demo.html`。
静态页无需构建，Pages 可直接服务。

## 六、推之前自检（10 秒）

```bash
cd /Users/hashmai/roost-im/roost-ui-arch
git status --short            # 应为空
node tools/test_sim.js        # 9/9
python3 tools/check_seat_ids.py --require-unified   # seats=23 zones=8 fail=0
git ls-files | wc -l          # 84
```

## 七、仓库里做了什么（为什么现在符合规范）

| GitHub 社区规范项 | 状态 | 文件 |
| --- | --- | --- |
| 许可证 | ✅ | `LICENSE`（Apache-2.0）+ `NOTICE` |
| README（含用法/截图/结构） | ✅ | `README.md`、`README.en.md` |
| 贡献指南 | ✅ | `CONTRIBUTING.md` |
| 行为准则 | ✅ | `CODE_OF_CONDUCT.md`（Contributor Covenant 2.1） |
| 安全策略 | ✅ | `SECURITY.md` |
| Issue 模板 | ✅ | `.github/ISSUE_TEMPLATE/bug_report.yml`、`feature_request.yml`、`config.yml` |
| PR 模板 | ✅ | `.github/PULL_REQUEST_TEMPLATE.md` |
| CODEOWNERS | ✅ | `.github/CODEOWNERS` |
| CI | ✅ | `.github/workflows/ci.yml`（3 个 job） |
| 更新日志 | ✅ | `CHANGELOG.md` |
| 第三方授权 | ✅ | `THIRD-PARTY-NOTICES.md` |
| .gitignore / .gitattributes / .editorconfig | ✅ | 根目录 |
| 无凭据、无个人素材、无大文件 | ✅ | 见合规报告 |
