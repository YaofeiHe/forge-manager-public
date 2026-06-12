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
5. dashboard 在本地启动只读可视化视图。

## 关键运行与同步约束

- 所有项目状态回答必须来自本地 CLI 输出，不从记忆直接作答。
- 任何 GitHub/Feishu 外部同步都建立在本地工件、可审计 baseline 和真实认证之上。
- 当前这次初始化补齐不改变现有代码结构；后续若新增模块或命令，需要同步更新本文件和操作指南。
