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

- 不读取密码、cookie、token、SSH key、浏览器 profile、`.env` 或其他私密凭据内容。
- 不绕过 GitHub 登录、Feishu 授权、CAPTCHA、2FA 或平台风控。
- 不因为补初始化而重排现有源码结构、修改包名、变更 CLI 参数或重写配置格式。
- GitHub public 发布必须显式确认；private 同步也必须建立在可审计 baseline 和 secret scan 之上。

## 默认更新约束

- 需求变化时先更新本文件，再根据需要同步更新 `docs/project-overview.md` 与 `docs/operation-guide.md`。
- 目录结构、模块职责或数据源变化时刷新 `docs/project-overview.md`。
- workflow 入口、同步流程或维护命令变化时刷新 `docs/operation-guide.md`。
- 长期文档默认作为飞书同步对象；若飞书配置缺失，应明确 blocked，不得伪造同步完成。

## 当前初始化基线

- 已建立本地 git baseline，最近 baseline commit 为 `d0c24f6`。
- 已写入 `.github/nexus-sync.json`，目标 private/public 仓库分别为 `<PRIVATE_REPO>` 和 `YaofeiHe/forge-manager-public`。
- 本地文档和 `.nexus/project-intent.json` 已补齐；真实 GitHub bootstrap、private push、Feishu 发布仍依赖外部认证与权限。

## 原始输入摘要

完成 forge-manager 没有遵循 nexus 初始化要求做的地方，注意不要改动 forge-manager 现有项目结构，而是做一些，比如操作指南补全，github 同步补全之类的事情（注意可能不止这些）。

## Nexus 补充初始化记录

本节由补充初始化追加，用于补齐缺失的说明结构；已有正文保留不改。

## 规范化目标

`forge-manager` 应作为一个由 Nexus 初始化和维护的真实项目，服务于中文互联网求职、网申流程、岗位信息整理、自动化执行前的安全规划和项目记录管理。
