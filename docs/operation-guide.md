# forge-manager 整体操作指南

目标类型：`project`

## 定位

`forge-manager` 是由 Nexus 管理或初始化的项目，应拥有可运行代码、git 基线、GitHub private 默认同步和整体操作指南。

## 项目意图说明

- 原始意图需求固定存放于 `docs/intent/original-requirement.md`。
- 完整规范化需求主文档固定存放于 `docs/intent/normalized-requirement.md`。
- 项目说明文档固定存放于 `docs/project-overview.md`。
- 整体操作指南固定存放于 `docs/operation-guide.md`。
- 机器可读索引固定存放于 `.nexus/project-intent.json`。

### 原始意图摘录

# forge-manager 原始意图需求

- 记录时间：`2026-06-07T19:16:41Z`
- 来源 run：`<NEXUS_RUN_ID>`
- 外部意图来源：`未显式提供`

## 原始输入

完成 forge-manager 没有遵循 nexus 初始化要求做的地方，注意不要改动 forge-manager 现有项目结构，而是做一些，比如操作指南补全，github 同步补全之类的事情（注意可能不止这些）。

### 规范化意图摘录

# forge-manager 规范化意图需求

- 记录时间：`2026-06-07T19:16:41Z`
- 来源 run：`<NEXUS_RUN_ID>`
- 项目路径：`<PROJECT_ROOT>`
- GitHub private 默认同步：`enabled`
- GitHub private 仓库：`<PRIVATE_REPO>`
- GitHub public 仓库：`YaofeiHe/forge-manager-public`
- 飞书文档同步：`enabled`
- 参考意图来源：`未显式提供`

## 文档职责

- `docs/intent/original-requirement.md`：保留用户原始要求，作为后续更新的可追溯依据。
- `docs/intent/normalized-requirement.md`：维护当前有效的项目范围、约束和初始化要求。
- `docs/project-overview.md`：记录实际代码结构、模块职责和运行入口。
- `docs/operation-guide.md`：记录日常操作、同步和维护流程。
- `docs/feishu-records.md`：记录飞书同步和文档更新事件。

## 项目定位

`forge-manager` 是一个本地项目管理聚合器，用来扫描 `forge` 工作区里的真实项目、Git 仓库、Codex 会话、Nexus Lab 运行结果和 Verix 工件，并输出结构、状态、项目视图和轻量 dashboard。

## 项目命名说明

- 项目当前使用名称 `forge-manager`，因为用户已经显式使用该名称并围绕它建立了 CLI、skill 和配置。
- 含义：管理 `forge` 工作区内多个项目及其相关工作项。
- 记忆点：`forge` 是工作区，`manager` 是聚合视图与记录入口。
- 采用理由：名称直接对应当前职责，不需要改目录、不需要迁移包名。

## 本次补齐目标

- 不调整现有代码目录和包结构，只补齐 Nexus 初始化缺失的管理产物。
- 建立可审计 git baseline，并为 GitHub private/public 同步补齐配置。
- 补齐项目意图文档、项目说明文档、整体操作指南、飞书记录流和机器可读索引。
- 保持 `forge-manager` 现有 CLI、配置文件、数据库路径和 skill 入口不变。

## 项目范围

- 提供 `scan`、`structure`、`status`、`project`、`record`、`link`、`branch`、`invoke`、`dashboard` 等本地命令。
- 从 `config/projects.toml` 解析受管项目路径，并基于 `data/forge-manager.sqlite` 持久化扫描结果。
- 采集真实本地数据，包括文件系统、Git、Codex、Nexus Lab 和 Verix 工件。
- 输出树状图、多层级列表和单项目报告，用于项目群管理和调度。

## 默认能力边界

- 项目是本地管理工具，不负责替代 Nexus 或 Verix 的真实 workflow 执行。
- 项目默认保留 GitHub private 同步配置和 Feishu 文档同步入口，但外部认证、建仓、push、发布仍受审批和真实凭据约束。
- 操作指南、项目说明和规范化需求属于长期文档，后续每次结构或流程变化都应同步更新。

## 硬安全边界

- 不读取密码、cookie、token、SSH key、浏览

...（已截断，完整内容见对应意图文档）

### 项目说明摘录

# forge-manager 项目说明

- 更新时间：`2026-06-07T19:16:41Z`
- 项目路径：`<PROJECT_ROOT>`
- GitHub private：`<PRIVATE_REPO>` (`enabled`)
- GitHub public：`YaofeiHe/forge-manager-public`
- Feishu 长期文档同步：`enabled`

## 项目定位

`forge-manager` 是 `forge` 工作区的本地项目管理器。它扫描真实本地项目与运行工件，把它们整理成统一的工作项数据库，并通过 CLI 与 dashboard 输出结构、状态和项目进度。

## 文档体系

- `docs/intent/original-requirement.md`：原始需求归档。
- `docs/intent/normalized-requirement.md`：规范化需求主文档。
- `docs/project-overview.md`：项目说明文档。
- `docs/operation-guide.md`：整体操作指南。
- `docs/feishu-records.md`：飞书同步记录流。

## 关键目录与文件

- `forge-manager`：可执行入口脚本，调用包内 CLI。
- `src/forge_manager/cli.py`：命令行主入口和自然语言路由。
- `src/forge_manager/config.py`：加载 `config/projects.toml`、工作区根路径、Codex home 与数据库路径。
- `src/forge_manager/collectors/`：采集 filesystem、git、codex、nexus-lab、verix 等真实本地数据源。
- `src/forge_manager/reports/`：渲染结构报告、状态报告和单项目报告。
- `src/forge_manager/dashboard/`：提供本地 dashboard Web 服务。
- `src/forge_manager/db.py` 与 `src/forge_manager/models.py`：定义持久化与领域模型。
- `config/projects.toml`：声明工作区根路径和受管项目映射。
- `skills/forge-manager-workflow/SKILL.md`：Codex 侧 skill 入口，要求一律走本地 CLI。
- `data/forge-manager.sqlite`：扫描后的本地数据库。
- `.nexus/`：本项目的 board、intent 索引和 autosync 元数据。
- `.github/nexus-sync.json`：GitHub private/public 同步配置。

## 当前目录结构摘要

- `.github/`
- `.nexus/`
- `config/`
- `data/`
- `docs/`
- `skills/`
- `src/`
- `forge-manager`
- `pyproject.toml`

## 核心运行流

1. `forge-manager` CLI 读取 `config/projects.toml`。
2. collectors 扫描本地项目、Git、Codex、Nexus Lab 和 Verix 产物。
3. 数据写入 `data/forge-manager.sqlite`。
4. reports 根据数据库生成结构、状态和项目详情输出。
5.

...（已截断，完整内容见对应意图文档）

## Skill 入口

```text
$nexus-workflow 为项目 <PROJECT_ROOT> 生成整体操作指南
$nexus-workflow 同步项目 <PROJECT_ROOT> 的整体操作指南到飞书
$nexus-workflow 将项目 <PROJECT_ROOT> 同步到 GitHub public，确认 public 发布
```

## 初始化与日常更新

- 新项目初始化应创建真实项目目录，并在默认情况下初始化 git。
- GitHub private 同步是默认能力；只有指令显式写“不同步 GitHub”、“跳过 GitHub 同步”、`no-github-sync`，或 CLI 使用 `--no-github-sync` 时才跳过。
- Feishu 是操作指南、说明文档和初始化/更新记录的发布通道；初始化项目时默认写入 `docs/feishu-records.md` 并同步到飞书，只有指令显式写“不同步飞书”、“跳过飞书”、`no-feishu-sync`，或 CLI 使用 `--no-feishu-sync` 时才跳过。
- 激活 `$nexus-workflow` 后，每次对项目内容产生更新，都应默认触发飞书自动同步：优先更新已有线上文档，没有对应绑定时才新建，不能把同一份说明拆成多份重复文件。
- 如果飞书配置不可用，应 blocked 到 setup/doctor，不应假装写入成功；本地记录和本地指南仍需保留为 artifact。
- GitHub public 发布永远需要显式确认，不能跟随 private 自动发布。

## GitHub 同步

private 仓库：`<PRIVATE_REPO>`

public 仓库：`YaofeiHe/forge-manager-public`

GitHub CLI 未认证或 token 失效时，workflow 使用原生 GitHub CLI 浏览器登录：

```bash
gh auth login --web --clipboard --skip-ssh-key --git-protocol https --hostname github.com
```

用户手动完成邮箱、密码、2FA、CAPTCHA 和授权确认。workflow 不读取本地邮箱、密码、token、cookie、浏览器 profile、SSH key、`.env` 或 2FA/CAPTCHA 内容。

### GitHub 登录与同步经验

- 如果 `gh auth login --web` 在 `https://github.com/login/device/code` 阶段返回 EOF，不要立即让用户重复登录；workflow 应先复查 `gh auth status --hostname github.com`，因为设备授权可能已经成功写入 GitHub CLI 状态。
- 如果登录启动失败包含代理、`127.0.0.1`、`operation not permitted`、`dial tcp` 或 EOF，优先复用 recovery playbook 的 `retry_without_proxy_and_debug_api` 方向：绕开代理并开启 `GH_DEBUG=api` 后再次发起 GitHub CLI 官方 web/device 登录。
- 如果 GitHub 仓库创建失败，先检查是否为同名 private/public 仓库已存在；若 `gh repo view` 可访问，应复用现有仓库、补齐 remote，并重试原 bootstrap/sync，不要默认更换仓库名。
- 如果 `git push` 看似卡住或失败，先收口检查本地 commit、remote、GitHub 仓库可访问性和 `gh auth setup-git --hostname github.com`；确认凭证桥接可用后再重试原 private/public sync。
- GitHub 登录、建仓、凭证桥接、push、public staging/secret scan 任一环节失败时，应先查项目 `.nexus/recovery-playbook.json` 和内置经验；命中经验先按对应方向尝试或发起提权，仍失败才调用高精度恢复模块。
- 如果没有精确命中的经验，高精度恢复模块应读取相关经验库条款和历史操作结果作为参考证据，先判断经验是否与当前情景有关、是否仍有效、是否值得尝试；经验无关时应直接丢弃并自主规划新路线，不能被经验库限制住。

public 发布必须先生成 staging，并通过 secret scan。`.env`、token、key、cookie、apikey、本地运行数据、`.data`、`.codex`、`.agents` 等不能进入 public。

## Feishu 同步

- 本指南的主文件是 `docs/operation-guide.md`。
- 同步到飞书时，应优先把本地 Markdown 文件上传并通过 Drive import task 导入为飞书云文档，以保留 Markdown 标题、列表、代码块等结构。
- Markdown 导入需要 folder_token 作为目标文件夹；仅配置 doc_token 时不能保真导入 `.md`。
- 飞书同步应维护 `.nexus/feishu-documents.json`，按本地 Markdown 路径绑定线上 docx；有效绑定存在时更新同一文档，不重复创建。
- 初始化和日常更新记录统一写入 `docs/feishu-records.md`，不应为每一次记录生成一份独立飞书文档。
- 如果绑定文档已删除、失效或资源不可访问，且 folder_token 可用，workflow 应在同一条同步指令内自动标记旧绑定为 stale、重新导入新文档并更新绑定。
- 只有缺凭证、缺 folder_token、缺 API 权限、缺资源权限或网络不可用等真实外部条件时才 blocked；blocked 的下一步提示必须指向真实缺口，并回到原同步指令重试。
- 缺少 `.nexus/feishu.json`、app_id/app_secret、folder_token、`docs:document.media:upload`/Drive 导入上传权限或文件夹资源权限时，应返回明确 blocked reason。
- Feishu 配置和权限问题由 `feishu setup` / `feishu doctor` 处理，不使用 mock 替代。

## 验收边界

- GitHub private/bootstrap/auth/secret scan 已作为基础能力验证；日常变更不重复跑完整 GitHub private E2E。
- Nexus 自身指南同步飞书可以作为本机真实 Feishu 自同步测试。
- Verix 飞书同步、Nexus 初始化新项目后的飞书同步、public 发布由后续 `$` 指令验收。

## 机器可读上下文

```json
{
  "schema": "nexus.operation_guide_context.v1",
  "project": "forge-manager",
  "target": "project",
  "private_repo": "<PRIVATE_REPO>",
  "public_repo": "YaofeiHe/forge-manager-public",
  "updated_at": "2026-06-12T08:21:01.578702+00:00"
}
```
