from __future__ import annotations

from collections import defaultdict
import re
import sqlite3

from forge_manager.db import Store


ACTIVE_STATUSES = {"running", "stale", "planned", "blocked", "unknown"}


def activity_report(
    store: Store,
    start_ts: int,
    end_ts: int,
    view: str = "list",
    project_id: str | None = None,
    active_only: bool = True,
    query: str = "",
    statuses: set[str] | None = None,
    summarize: bool = False,
) -> str:
    with store.connect() as conn:
        items = conn.execute("select * from work_items").fetchall()
        item_by_id = {row["id"]: row for row in items}
        project_ids = {row["id"] for row in items if row["kind"] == "project"}
        user_events = conn.execute(
            """
            select e.*, w.name, w.status, w.parent_id, w.kind, w.goal, w.next_action
            from events e
            join work_items w on w.id=e.work_item_id
            where e.timestamp between ? and ?
              and e.source_type='codex'
              and e.event_type='user_message'
            order by e.timestamp desc
            """,
            (start_ts, end_ts),
        ).fetchall()
        detail_events = conn.execute(
            """
            select e.*, w.name, w.status, w.parent_id, w.kind, w.goal, w.next_action
            from events e
            join work_items w on w.id=e.work_item_id
            where e.timestamp between ? and ?
              and e.source_type='codex'
              and e.event_type in ('user_message', 'assistant_message', 'task_complete')
            order by e.timestamp desc
            """,
            (start_ts, end_ts),
        ).fetchall()
        status_events = conn.execute(
            """
            select e.*, w.name, w.status, w.parent_id, w.kind, w.goal, w.next_action
            from events e
            join work_items w on w.id=e.work_item_id
            where e.timestamp between ? and ?
              and (
                (e.source_type='codex' and e.event_type='thread_status')
                or (
                  w.status in ('running', 'stale', 'planned', 'blocked', 'unknown')
                  and w.kind not in ('project', 'workspace')
                  and e.source_type not in ('git', 'filesystem')
                )
              )
            order by e.timestamp desc
            """,
            (start_ts, end_ts),
        ).fetchall()
        links = conn.execute("select * from links where link_type in ('codex_rollout', 'codex_thread')").fetchall()

    rollout_by_item = {row["work_item_id"]: row["target"] for row in links if row["link_type"] == "codex_rollout"}
    thread_by_item = {row["work_item_id"]: row["target"] for row in links if row["link_type"] == "codex_thread"}
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"events": [], "detail_events": [], "status_events": [], "items": {}})
    for event in user_events:
        project = _project_for_item(item_by_id, project_ids, event["work_item_id"])
        if project_id and project != project_id:
            continue
        grouped[project]["events"].append(event)
        grouped[project]["items"][event["work_item_id"]] = item_by_id[event["work_item_id"]]
    for event in detail_events:
        project = _project_for_item(item_by_id, project_ids, event["work_item_id"])
        if project_id and project != project_id:
            continue
        grouped[project]["detail_events"].append(event)
        grouped[project]["items"][event["work_item_id"]] = item_by_id[event["work_item_id"]]
    for event in status_events:
        project = _project_for_item(item_by_id, project_ids, event["work_item_id"])
        if project_id and project != project_id:
            continue
        if active_only and event["status"] not in ACTIVE_STATUSES:
            continue
        grouped[project]["status_events"].append(event)
        grouped[project]["items"][event["work_item_id"]] = item_by_id[event["work_item_id"]]

    if not grouped:
        target = f" for {project_id}" if project_id else ""
        return f"No matching conversations/tasks found{target} in range {start_ts} - {end_ts}."

    lines = [f"Activity range: {start_ts} - {end_ts}"]
    if project_id:
        lines.append(f"Project filter: {project_id}")
    if query:
        lines.append(f"Task query: {query}")
    if statuses:
        lines.append("Status filter: " + ", ".join(sorted(statuses)))
    lines.append("")

    emitted = False
    for project in sorted(grouped):
        bucket = grouped[project]
        rows = [row for row in bucket["items"].values() if _is_codex_task(row)]
        if active_only:
            rows = [row for row in rows if row["status"] in ACTIVE_STATUSES]
        if statuses:
            rows = [row for row in rows if row["status"] in statuses]
        if query:
            scored = [
                (row, _match_score(row, query, bucket["events"], bucket["detail_events"], bucket["status_events"]))
                for row in rows
            ]
            rows = [
                row
                for row, score in scored
                if score >= _required_score(query) and not _is_internal_model_node(row, query)
            ]
        if not rows:
            continue
        emitted = True
        lines.append(f"- 项目：{project}")
        rows = sorted(
            rows,
            key=lambda item: (
                _match_score(item, query, bucket["events"], bucket["detail_events"], bucket["status_events"]) if query else 0,
                item["updated_at"],
            ),
            reverse=True,
        )
        for row in rows[:8]:
            latest = _latest_message_for_item(bucket["events"], row["id"])
            status_message = _latest_status_for_item(bucket["status_events"], row["id"])
            result_message = _latest_result_for_item(bucket["detail_events"], row["id"])
            content = _task_content(row, latest)
            result = _task_result(row, latest, status_message, result_message)
            rollout = rollout_by_item.get(row["id"])
            thread = thread_by_item.get(row["id"])
            lines.extend(_task_block(row, content, result, rollout, thread))
        lines.append("")

    if not emitted:
        target = f" for {project_id}" if project_id else ""
        return f"No matching conversations/tasks found{target} in range {start_ts} - {end_ts}."
    return "\n".join(lines).rstrip()


def _project_for_item(item_by_id: dict[str, sqlite3.Row], project_ids: set[str], item_id: str) -> str:
    current = item_by_id.get(item_id)
    while current:
        if current["id"] in project_ids:
            return current["id"]
        parent_id = current["parent_id"]
        current = item_by_id.get(parent_id) if parent_id else None
    return "forge"


def _task_block(row: sqlite3.Row, content: str, result: str, rollout: str | None, thread: str | None) -> list[str]:
    title = _display_task_name(str(row["name"]))
    deep_link = f"codex://threads/{thread}" if thread else "未记录"
    source = rollout or "未记录"
    return [
        f"  - 任务：{title} [{row['status']}]",
        f"    - 深度链接：{deep_link}",
        f"    - 源文件：{source}",
        f"    - 内容：{content}",
        f"    - 结果：{result}",
    ]


def _display_task_name(name: str) -> str:
    if name.startswith("codex:"):
        name = name.removeprefix("codex:")
    return _compact(name, 96)


def _latest_message_for_item(events: list[sqlite3.Row], item_id: str) -> str:
    for event in events:
        if event["work_item_id"] == item_id:
            return _request_text(event["message"])
    return ""


def _latest_status_for_item(events: list[sqlite3.Row], item_id: str) -> str:
    for event in events:
        if event["work_item_id"] == item_id:
            return event["message"]
    return ""


def _latest_result_for_item(events: list[sqlite3.Row], item_id: str) -> str:
    for kind in ("task_complete", "assistant_message"):
        for event in events:
            if event["work_item_id"] == item_id and event["event_type"] == kind:
                return _request_text(event["message"])
    return ""


def _is_codex_task(row: sqlite3.Row) -> bool:
    return row["kind"] == "run" and str(row["name"]).startswith("codex:")


def _is_internal_model_node(row: sqlite3.Row, query: str) -> bool:
    explicit_internal_query = any(marker in query for marker in ("模型节点", "intent_route", "JSON Schema", "kernel"))
    if explicit_internal_query:
        return False
    text = " ".join(str(row[column] or "") for column in ("name", "goal", "next_action"))
    return "nexus workflow kernel 的模型节点" in text or "请严格返回符合 JSON Schema 的 JSON 对象" in text


def _matches_query(row: sqlite3.Row, query: str, events: list[sqlite3.Row], status_events: list[sqlite3.Row]) -> bool:
    return _match_score(row, query, events, [], status_events) >= _required_score(query)


def _match_score(
    row: sqlite3.Row,
    query: str,
    user_events: list[sqlite3.Row],
    detail_events: list[sqlite3.Row],
    status_events: list[sqlite3.Row],
) -> int:
    needle = query.strip().lower()
    if not needle:
        return 1
    title_chunks = [_request_text(row["name"] or ""), _request_text(row["goal"] or ""), _request_text(row["next_action"] or "")]
    user_chunks = [_request_text(event["message"]) for event in user_events if event["work_item_id"] == row["id"]]
    result_chunks = [
        _request_text(event["message"])
        for event in detail_events
        if event["work_item_id"] == row["id"] and event["event_type"] in {"assistant_message", "task_complete"}
    ]
    status_chunks = [_request_text(event["message"]) for event in status_events if event["work_item_id"] == row["id"]]
    score = 0
    if _chunks_match(needle, title_chunks):
        score += 3
    if _chunks_match(needle, user_chunks):
        score += 3
    if _chunks_match(needle, result_chunks):
        score += 5
    if _chunks_match(needle, status_chunks):
        score += 1
    return score


def _chunks_match(needle: str, chunks: list[str]) -> bool:
    haystack = _normalize_search_text(" ".join(chunk or "" for chunk in chunks))
    if not haystack:
        return False
    normalized_needle = _normalize_search_text(needle)
    if normalized_needle in haystack:
        return True
    tokens = _query_tokens(normalized_needle)
    if not tokens:
        return False
    if len(tokens) <= 2:
        return all(token in haystack for token in tokens)
    matches = sum(1 for token in tokens if token in haystack)
    return matches >= _minimum_token_matches(tokens)


def _required_score(query: str) -> int:
    tokens = _query_tokens(query)
    return 3 if len(tokens) <= 2 else 5


def _minimum_token_matches(tokens: list[str]) -> int:
    if len(tokens) <= 4:
        return min(3, len(tokens))
    return min(4, len(tokens))


def _query_tokens(query: str) -> list[str]:
    normalized = _normalize_search_text(query)
    for char in "“”\"'（）()[]【】<>《》/\\|，,。；;、：:":
        normalized = normalized.replace(char, " ")
    stop_words = {"任务", "完整", "继续", "有关", "相关", "关于", "全部", "所有", "all", "history"}
    tokens = []
    seen = set()
    for token in normalized.split():
        if len(token) < 2 or token in stop_words or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _normalize_search_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"([a-z0-9_.-])([\u4e00-\u9fff])", r"\1 \2", normalized)
    normalized = re.sub(r"([\u4e00-\u9fff])([a-z0-9_.-])", r"\1 \2", normalized)
    return normalized


def _task_content(row: sqlite3.Row, latest: str) -> str:
    raw = row["goal"] or latest or row["name"]
    return _compact(_request_text(raw), 120)


def _task_result(row: sqlite3.Row, latest: str, status_message: str, result_message: str = "") -> str:
    status = row["status"]
    result_detail = _compact(_request_text(result_message), 180) if result_message else ""
    status_detail = row["next_action"] or status_message or latest
    status_detail = _compact(_request_text(status_detail), 120) if status_detail else ""
    if result_detail:
        if status in {"running", "stale", "planned", "blocked", "unknown"}:
            return f"{_status_label(status)}；最新可见结果：“{result_detail}”"
        return result_detail
    detail = status_detail
    if status == "running":
        return f"仍在运行{_suffix_latest(detail)}"
    if status == "stale":
        return f"未完成且长期无更新{_suffix_latest(detail)}"
    if status == "planned":
        return f"处于计划状态{_suffix_latest(detail)}"
    if status == "blocked":
        return f"被阻断{_suffix_latest(detail)}"
    if status == "unknown":
        return f"结果未知{_suffix_latest(detail)}"
    if status == "idle":
        return f"当前空闲或最近记录已完成{_suffix_latest(detail)}"
    if status == "archived":
        return f"已归档{_suffix_latest(detail)}"
    return f"状态为 {status}{_suffix_latest(detail)}"


def _status_label(status: str) -> str:
    labels = {
        "running": "索引状态为 running",
        "stale": "索引状态为 stale",
        "planned": "索引状态为 planned",
        "blocked": "索引状态为 blocked",
        "unknown": "索引状态为 unknown",
    }
    return labels.get(status, f"索引状态为 {status}")


def _suffix_latest(detail: str) -> str:
    if not detail:
        return ""
    return f"，最新记录为“{detail}”"


def _compact(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _request_text(text: str) -> str:
    markers = ("## My request for Codex:", "My request for Codex:")
    found_request_marker = False
    for marker in markers:
        if marker in text:
            text = text.split(marker, 1)[1]
            found_request_marker = True
            break
    stop_markers = ("<skill>", "# Context from my IDE setup:", "## Open tabs:")
    for marker in stop_markers:
        if marker in text:
            text = text.split(marker, 1)[0]
    if not found_request_marker:
        if text.lstrip().startswith("<environment_context>"):
            return ""
        text = re.sub(r"<environment_context>.*?</environment_context>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<filesystem>.*?</filesystem>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<INSTRUCTIONS>.*?</INSTRUCTIONS>", " ", text, flags=re.DOTALL)
    return text.strip()
