from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from forge_manager.collectors import collect_codex, collect_filesystem, collect_git, collect_nexus_lab, collect_verix
from forge_manager.config import load_config
from forge_manager.dashboard.app import serve_dashboard
from forge_manager.db import Store, now
from forge_manager.reports import activity_report, capabilities_report, project_report, status_report, structure_report
from forge_manager.reports.status import day_bounds, range_bounds, rolling_days_bounds, rolling_hours_bounds


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.manager_root)
    store = Store(config.db_path)
    store.init()
    if args.command == "scan":
        scan(config, store)
        print(f"scan complete: {config.db_path}")
        return 0
    if args.command == "structure":
        scan(config, store)
        print(structure_report(store, args.view, args.active))
        return 0
    if args.command == "status":
        scan(config, store)
        start, end = day_bounds() if args.period == "today" else range_bounds(args.from_date, args.to_date)
        print(status_report(store, start, end, args.view))
        return 0
    if args.command == "activity":
        scan(config, store)
        start, end = day_bounds() if args.period == "today" else range_bounds(args.from_date, args.to_date)
        print(activity_report(store, start, end, args.view, args.project, not args.all))
        return 0
    if args.command == "capabilities":
        scan(config, store)
        print(capabilities_report(config, store, args.view))
        return 0
    if args.command == "project":
        scan(config, store)
        print(project_report(store, args.project_id, args.view))
        return 0
    if args.command == "record":
        record(store, args)
        print("recorded")
        return 0
    if args.command == "link":
        link(store, args)
        print("linked")
        return 0
    if args.command == "branch":
        branch(store, args)
        print("branch updated")
        return 0
    if args.command == "invoke":
        return invoke(config, store, args.text)
    if args.command == "dashboard":
        scan(config, store)
        serve_dashboard(config, store, args.host, args.port)
        return 0
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge-manager")
    parser.add_argument("--manager-root", type=Path)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan")

    structure = sub.add_parser("structure")
    structure.add_argument("--view", choices=["list", "tree"], default="tree")
    structure.add_argument("--active", action="store_true")

    status = sub.add_parser("status")
    status.add_argument("period", nargs="?", default="today", choices=["today", "range"])
    status.add_argument("--from", dest="from_date", default=None)
    status.add_argument("--to", dest="to_date", default=None)
    status.add_argument("--view", choices=["list", "tree"], default="list")

    activity = sub.add_parser("activity")
    activity.add_argument("period", nargs="?", default="today", choices=["today", "range"])
    activity.add_argument("--from", dest="from_date", default=None)
    activity.add_argument("--to", dest="to_date", default=None)
    activity.add_argument("--project", default=None)
    activity.add_argument("--all", action="store_true", help="include idle and archived conversations touched in the range")
    activity.add_argument("--view", choices=["list", "tree", "markdown"], default="list")

    capabilities = sub.add_parser("capabilities")
    capabilities.add_argument("--view", choices=["list"], default="list")

    project = sub.add_parser("project")
    project.add_argument("project_id")
    project.add_argument("--view", choices=["list", "tree", "markdown"], default="list")

    record_p = sub.add_parser("record")
    record_sub = record_p.add_subparsers(dest="record_type", required=True)
    for kind in ("blocker", "decision", "next"):
        item = record_sub.add_parser(kind)
        item.add_argument("work_item_id")
        item.add_argument("message")

    link_p = sub.add_parser("link")
    link_sub = link_p.add_subparsers(dest="link_type", required=True)
    for kind in ("codex-thread", "nexus-lab-run", "verix-run", "file"):
        item = link_sub.add_parser(kind)
        item.add_argument("work_item_id")
        item.add_argument("target")
    git_branch = link_sub.add_parser("git-branch")
    git_branch.add_argument("work_item_id")
    git_branch.add_argument("repo_path")
    git_branch.add_argument("branch")

    branch_p = sub.add_parser("branch")
    branch_sub = branch_p.add_subparsers(dest="branch_command", required=True)
    create = branch_sub.add_parser("create")
    create.add_argument("project_id")
    create.add_argument("branch_id")
    create.add_argument("--kind", default="plan_variant")
    create.add_argument("--name", default=None)
    list_b = branch_sub.add_parser("list")
    list_b.add_argument("project_id")

    invoke_p = sub.add_parser("invoke")
    invoke_p.add_argument("text", nargs=argparse.REMAINDER)

    dashboard = sub.add_parser("dashboard")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    return parser


def scan(config, store: Store) -> None:
    collect_filesystem(config, store)
    collect_git(config, store)
    collect_codex(config, store)
    collect_nexus_lab(config, store)
    collect_verix(config, store)


def record(store: Store, args) -> None:
    message = args.message
    item_id = args.work_item_id
    if args.record_type == "blocker":
        store.mark_work_item(item_id, status="blocked", next_action=message)
        store.add_event(item_id, now(), "manual", "blocked", message, "warning")
    elif args.record_type == "decision":
        store.add_event(item_id, now(), "manual", "decision", message)
    elif args.record_type == "next":
        store.mark_work_item(item_id, status="idle", next_action=message)
        store.add_event(item_id, now(), "manual", "next_action", message)


def link(store: Store, args) -> None:
    link_type = args.link_type.replace("-", "_")
    target = args.target
    if args.link_type == "git-branch":
        target = f"{args.repo_path}:{args.branch}"
    store.add_link(args.work_item_id, link_type, target, args.link_type)
    store.add_event(args.work_item_id, now(), "manual", "link", f"{args.link_type}: {target}")


def branch(store: Store, args) -> None:
    if args.branch_command == "create":
        node_id = f"{args.project_id}:{args.branch_id}"
        store.upsert_work_item(
            node_id,
            "branch",
            args.name or args.branch_id,
            "planned",
            parent_id=args.project_id,
            goal=args.kind,
            source="manual",
        )
        store.add_event(node_id, now(), "manual", "branch_created", f"{args.kind}: {args.name or args.branch_id}")
    elif args.branch_command == "list":
        with store.connect() as conn:
            rows = conn.execute("select id, name, status, goal from work_items where parent_id=? and kind='branch' order by name", (args.project_id,)).fetchall()
        for row in rows:
            print(f"{row['id']} [{row['status']}] {row['name']} {row['goal']}")


def invoke(config, store: Store, text_parts: list[str]) -> int:
    text = " ".join(text_parts).strip()
    scan(config, store)
    view = _view_for_text(text)
    search_intent = _asks_for_task_summary(text) or _asks_for_task_search(text)
    project_id = _project_filter_for_text(config, text, strict=search_intent)
    if _asks_for_capabilities(text):
        print(capabilities_report(config, store, view))
        return 0
    if _asks_for_structure(text):
        print(structure_report(store, view, active=True))
        return 0
    if _asks_for_task_summary(text) or _asks_for_task_search(text) or _asks_for_activity(text, project_id):
        start, end = _time_bounds_for_text(text)
        active_only = not _asks_for_all_tasks(text)
        statuses = _statuses_for_text(text)
        query = _query_for_text(config, text, project_id=project_id) if search_intent else ""
        print(
            activity_report(
                store,
                start,
                end,
                view,
                project_id,
                active_only=active_only,
                query=query,
                statuses=statuses,
                summarize=_asks_for_task_summary(text),
            )
        )
        return 0
    if "今天" in text or "今日" in text:
        start, end = day_bounds()
        print(status_report(store, start, end, view))
        return 0
    if "进度" in text or "项目" in text:
        tokens = [t.strip(" ，,。") for t in text.split()]
        for token in tokens:
            if token and token not in {"查看", "项目", "进度", "用多层级列表", "用树状图"}:
                report = project_report(store, token, view)
                if "not found" not in report:
                    print(report)
                    return 0
        print(structure_report(store, view, active=True))
        return 0
    print(structure_report(store, view, active=True))
    return 0


def _asks_for_activity(text: str, project_id: str | None = None) -> bool:
    markers = (
        "活跃状态",
        "活跃项目",
        "活跃的对话",
        "活跃对话",
        "活跃任务",
        "一天内",
        "24小时",
        "今日任务",
        "今天问过",
        "项目状态",
        "任务状态",
        "对话状态",
        "项目进度",
        "任务进度",
        "对话进度",
    )
    if any(marker in text for marker in markers):
        return True
    if project_id and not _asks_for_structure(text) and not _asks_for_capabilities(text):
        return "项目" in text or "任务" in text or "对话" in text or "状态" in text or "进度" in text
    return False


def _view_for_text(text: str) -> str:
    if any(marker in text for marker in ("markdown", "Markdown", "深度链接", "索引", "可索引")):
        return "markdown"
    if "树" in text:
        return "tree"
    return "list"


def _asks_for_structure(text: str) -> bool:
    return "结构" in text or "树状图" in text or "运行项目结构" in text


def _asks_for_capabilities(text: str) -> bool:
    if "能力" in text:
        return True
    return "子项目" in text and "简要列表" in text


def _asks_for_all_tasks(text: str) -> bool:
    return any(marker in text for marker in ("所有", "全部", "历史", "归档", "已完成"))


def _asks_for_task_search(text: str) -> bool:
    return any(marker in text for marker in ("查找", "匹配", "定位", "搜索", "快速匹配", "找到", "找出", "寻找"))


def _asks_for_task_summary(text: str) -> bool:
    return "总结" in text


def _time_bounds_for_text(text: str) -> tuple[int, int]:
    range_match = re.search(r"(\d{4}-\d{2}-\d{2}).{0,8}(\d{4}-\d{2}-\d{2})", text)
    if range_match:
        return range_bounds(range_match.group(1), range_match.group(2))
    if "今天" in text or "今日" in text:
        return day_bounds()
    if "昨天" in text:
        from datetime import datetime, timedelta
        from forge_manager.reports.status import TZ

        yesterday = datetime.now(TZ).date() - timedelta(days=1)
        return day_bounds(yesterday.isoformat())
    hours_match = re.search(r"(?:过去|近)?\s*(\d+)\s*小时", text)
    if hours_match:
        return rolling_hours_bounds(int(hours_match.group(1)))
    if "一天内" in text or "24小时" in text or "过去一天" in text or "近一天" in text:
        return rolling_hours_bounds(24)
    days_match = re.search(r"(?:过去|近)?\s*(\d+)\s*天", text)
    if days_match:
        return rolling_days_bounds(int(days_match.group(1)))
    return 0, now()


def _statuses_for_text(text: str) -> set[str] | None:
    statuses: set[str] = set()
    mapping = {
        "running": "running",
        "运行": "running",
        "stale": "stale",
        "过期": "stale",
        "长期无更新": "stale",
        "blocked": "blocked",
        "阻断": "blocked",
        "planned": "planned",
        "计划": "planned",
        "unknown": "unknown",
        "未知": "unknown",
        "idle": "idle",
        "空闲": "idle",
        "archived": "archived",
        "归档": "archived",
    }
    for marker, status in mapping.items():
        if marker in text:
            statuses.add(status)
    if "未完成" in text:
        statuses.update({"running", "stale", "planned", "blocked", "unknown"})
    if "已完成" in text:
        statuses.update({"idle", "archived"})
    return statuses or None


def _query_for_text(config, text: str, project_id: str | None = None) -> str:
    if "：" in text:
        return text.rsplit("：", 1)[1].strip()
    if ":" in text:
        return text.rsplit(":", 1)[1].strip()
    if "关于" in text:
        query = text.split("关于", 1)[1]
        for suffix in ("的任务", "的对话", "的项目", "任务", "对话", "项目"):
            query = query.replace(suffix, " ")
        query = " ".join(query.split())
        if query:
            return query
    query = text
    remove_phrases = [
        "按照项目-任务结构组织一个列表",
        "按照项目任务结构组织一个列表",
        "按项目-任务结构组织一个列表",
        "按项目任务结构组织一个列表",
        "按照项目-任务结构",
        "按照项目任务结构",
        "按项目-任务结构",
        "按项目任务结构",
        "项目内",
        "项目中",
        "项目里",
        "项目下",
        "按项目列出",
        "分项目列出",
        "组织一个列表",
        "组织列表",
        "按照markdown格式展示并加深度链接",
        "按照Markdown格式展示并加深度链接",
        "按照markdown格式展示",
        "按照Markdown格式展示",
        "用markdown格式展示",
        "用Markdown格式展示",
        "markdown格式",
        "Markdown格式",
        "加深度链接",
        "带深度链接",
        "深度链接",
        "显示源文件",
        "带源文件",
        "源文件",
        "可索引",
    ]
    for phrase in remove_phrases:
        query = query.replace(phrase, " ")
    remove_words = [
        "查找",
        "匹配",
        "定位",
        "搜索",
        "快速匹配",
        "找到",
        "找出",
        "寻找",
        "总结",
        "展示",
        "显示",
        "列表",
        "组织",
        "项目",
        "任务",
        "对话",
        "状态",
        "活跃",
        "所有",
        "全部",
        "历史",
        "归档",
        "已完成",
        "未完成",
        "今天",
        "今日",
        "昨天",
        "一天内",
        "24小时内",
        "24小时",
        "过去一天",
        "近一天",
        "有关",
        "相关",
        "关于",
        "并且",
        "的",
        "和",
    ]
    if project_id:
        profile = config.project_profiles.get(project_id)
        remove_words.extend([project_id, *(profile.aliases if profile else ())])
    for word in remove_words:
        query = query.replace(word, " ")
    query = re.sub(r"\b(?:内|中|里|下)\s+", " ", query)
    query = re.sub(r"(?:过去|近)?\s*\d+\s*(?:小时|天)", " ", query)
    query = re.sub(r"\d{4}-\d{2}-\d{2}", " ", query)
    query = re.sub(r"\b(running|stale|blocked|planned|unknown|idle|archived)\b", " ", query, flags=re.IGNORECASE)
    query = re.sub(r"[“”\"'（）()【】《》\[\]<>，,。；;、]", " ", query)
    query = " ".join(query.replace("：", " ").replace(":", " ").split())
    query = " ".join(token for token in query.split() if token not in {"内", "中", "里", "下"})
    return query


def _find_project_in_text(config, text: str) -> str | None:
    lowered = text.lower()
    for project_id, profile in config.project_profiles.items():
        keys = [project_id, *profile.aliases]
        if any(key and key.lower() in lowered for key in keys):
            return project_id
    return None


def _project_filter_for_text(config, text: str, *, strict: bool = False) -> str | None:
    if _asks_for_cross_project(text):
        return None
    if strict:
        return _explicit_project_filter_in_text(config, text)
    return _find_project_in_text(config, text)


def _asks_for_cross_project(text: str) -> bool:
    return any(marker in text for marker in ("所有项目", "全部项目", "跨项目", "全项目", "所有项目中", "全部项目中", "all projects", "All projects"))


def _explicit_project_filter_in_text(config, text: str) -> str | None:
    lowered = text.lower()
    for project_id, profile in config.project_profiles.items():
        keys = [project_id, *profile.aliases]
        for key in keys:
            if not key:
                continue
            escaped = re.escape(key)
            if re.search(rf"(?:项目|project)\s*[:：=]\s*{escaped}\b", lowered, re.IGNORECASE):
                return project_id
            if re.search(rf"{escaped}\s*(?:项目内|项目中|项目里|项目下|project only)", lowered, re.IGNORECASE):
                return project_id
            if re.search(rf"(?:只查|仅查|限定|限制到|只在|仅在)\s*{escaped}", lowered, re.IGNORECASE):
                return project_id
    return None


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
