---
name: forge-manager-workflow
description: Use when the user says "$forge-manager", "forge-manager", "管理项目的项目", "查看今天项目状态", "查看当前运行项目结构", "查看某项目进度", "记录项目阻断", or asks to query/manage forge project progress. This skill routes requests to the local forge-manager CLI at <PROJECT_ROOT> and must use real local data.
metadata:
  short-description: Query and manage forge project progress
---

# Forge Manager Workflow

Use the local CLI. Do not answer from memory when the user asks for project state.

Project root:

```bash
<PROJECT_ROOT>
```

Executable:

```bash
<PROJECT_ROOT>/forge-manager
```

## Required Behavior

- Always call the CLI for status, structure, project progress, records, links, branches, and dashboard actions.
- Do not fabricate project status. If the CLI returns `unknown`, report `unknown` and the stated reason.
- Do not create mock data or offline demos unless the user explicitly asks for mock/test mode.
- If a requested capability is unsupported, say so directly and give the supported replacement path.
- Do not claim the tool can reliably open the original Codex VS Code conversation unless a stable external interface is configured.

## Commands

Activity and task status:

```bash
./forge-manager activity today --view list
./forge-manager activity range --from YYYY-MM-DD --to YYYY-MM-DD --view list
./forge-manager activity range --from YYYY-MM-DD --to YYYY-MM-DD --project <project_id> --view list
./forge-manager activity range --from YYYY-MM-DD --to YYYY-MM-DD --all --view list
```

Task vocabulary:

- `project` means a forge child project such as `nexus`, `codpm`, or `forge-manager`.
- `task` means one Codex conversation window, represented by a `codex:` run item.
- `conversation` and `task` are equivalent in status, matching, and summary requests.
- Branch/worktree rows such as `git:main` or `worktree:*` are not tasks unless the user explicitly asks for branches or worktrees.

Default task semantics:

- If the user mentions project/task/conversation status without saying "all", treat it as active project/task status.
- Active task statuses are `running`, `stale`, `planned`, `blocked`, and `unknown`.
- `idle` and `archived` are included only when the user says "all", "history", "archived", or "completed".
- If the user specifies a project, list that project's conversation tasks by default, not only the project node.
- Task/activity output must be grouped by project. Each task item must use the standard task block with task name, status, deep link, source file, content, and result:

```text
- 项目：<project_id>
  - 任务：<conversation name without codex: prefix> [<status>]
    - 深度链接：codex://threads/<thread_id>  # or 未记录
    - 源文件：<rollout JSONL path>  # or 未记录
    - 内容：<task goal/request>
    - 结果：<current outcome/blocker/latest state>
```

Time semantics:

- `today` / `今日` means the current calendar day from 00:00:00 to 23:59:59.
- `24小时内`, `一天内`, `过去一天`, and `近一天` mean a rolling 24-hour window.
- `N小时内` / `过去N小时` means a rolling N-hour window.
- `N天内` / `过去N天` means a rolling N*24-hour window.
- An explicit date range uses that date range.

Matching and summary:

- Requests such as `查找`, `匹配`, `定位`, `搜索`, `快速匹配`, `找到`, `找出`, or `寻找` should filter conversation tasks by project, time, status, and keyword, and default to the standard project-task block output.
- Requests such as `总结 <task>` should match the relevant conversation history and summarize content, result, weak/incomplete points, and evidence using the same project-task block.
- Filters can be crossed, for example project + time + status + keyword.
- Search terms that contain a project name are not automatically project filters. For example, `查找所有项目中和 nexus workflow 恢复有关的任务` must search all projects with `nexus workflow 恢复` as keywords, not only the `nexus` project.
- Only explicit project-filter wording such as `nexus 项目内`, `项目：nexus`, `只查 nexus`, or the CLI `--project nexus` should restrict the result to one project.
- Search and summary should use real conversation evidence beyond the title when available: user messages, assistant visible results, `task_complete.last_agent_message`, thread status, and rollout source path.
- Exclude or down-rank tasks that only match because they are the current/previous forge-manager query task, system/developer instructions, skill text, or tool schema text.
- `codex://threads/<thread_id>` is a stable task index/deep link when the host Codex app supports it, but do not guarantee it opens the original window in every environment.
- `源文件` is the local rollout JSONL history source and should be preserved as the traceable fallback when a deep link is unavailable or unsupported.

Current project structure:

```bash
./forge-manager structure --active --view tree
./forge-manager structure --active --view list
./forge-manager structure --view tree
./forge-manager structure --view list
```

Today status:

```bash
./forge-manager status today --view list
./forge-manager status today --view tree
```

Date range:

```bash
./forge-manager status range --from YYYY-MM-DD --to YYYY-MM-DD --view list
```

Project progress:

```bash
./forge-manager project <project-or-work-item-id> --view list
./forge-manager project <project-or-work-item-id> --view tree
```

Manual records:

```bash
./forge-manager record blocker <work_item_id> '<reason>'
./forge-manager record decision <work_item_id> '<decision>'
./forge-manager record next <work_item_id> '<next action>'
```

Links:

```bash
./forge-manager link codex-thread <work_item_id> <thread_id>
./forge-manager link nexus-lab-run <work_item_id> <run_id>
./forge-manager link verix-run <work_item_id> <run_id>
./forge-manager link git-branch <work_item_id> <repo_path> <branch>
./forge-manager link file <work_item_id> <path>
```

Branches:

```bash
./forge-manager branch create <project_id> <branch_id> --kind <kind> --name '<display name>'
./forge-manager branch list <project_id>
```

Dashboard:

```bash
./forge-manager dashboard --host 127.0.0.1 --port 8765
```

## Natural Language Routing

For free-form `$forge-manager ...` requests, call:

```bash
./forge-manager invoke "<user request after $forge-manager>"
```

Examples:

```bash
./forge-manager invoke "今天项目状态"
./forge-manager invoke "查看当前运行项目结构，用树状图"
./forge-manager invoke "查看 nexus-lab 进度，用多层级列表"
./forge-manager invoke "列表展示24小时内活跃项目的状态"
./forge-manager invoke "列表展示 nexus 项目状态"
./forge-manager invoke "查找24小时内 nexus stale 任务：恢复"
./forge-manager invoke "总结 nexus 中关于恢复协议的任务"
```

## Data Sources

The CLI reads real local data:

- `<FORGE_ROOT>`
- `~/.codex/state_5.sqlite`
- `~/.codex/session_index.jsonl`
- `~/.codex/sessions/**/rollout-*.jsonl`
- `~/.codex/archived_sessions/*.jsonl`
- `nexus-lab/runs/*`
- `nexus-lab/cases/*`
- configured git repos and worktrees
- verix artifacts when a stable output is discoverable

## Output

Return the CLI output. If it is very long, summarize the high-signal parts and mention the command that produced the full output.

For task/activity requests, preserve the task-list semantics in the answer:

```text
- 项目：<project_id>
  - 任务：<conversation name without codex: prefix> [<status>]
    - 深度链接：codex://threads/<thread_id>  # or 未记录
    - 源文件：<rollout JSONL path>  # or 未记录
    - 内容：<request/goal>
    - 结果：<latest state/outcome>
```
