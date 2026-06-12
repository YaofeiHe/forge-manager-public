from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from typing import Any

from forge_manager.config import Config
from forge_manager.db import Store, now


STALE_SECONDS = 15 * 60


def collect_codex(config: Config, store: Store) -> None:
    db_path = config.codex_home / "state_5.sqlite"
    if not db_path.exists():
        store.add_event("forge", now(), "codex", "collector_error", f"Codex state db missing: {db_path}", "warning")
        return
    try:
        rows = _read_threads(db_path)
    except Exception as exc:
        store.add_event("forge", now(), "codex", "collector_error", f"Failed to read Codex state db: {exc}", "error")
        return
    for row in rows:
        thread_id = row["id"]
        rollout = Path(row["rollout_path"])
        cwd = row["cwd"] or ""
        rollout_events = _read_rollout_events(rollout)
        first_user_message = row["first_user_message"] or _first_user_message(rollout_events) or ""
        parent_id = _project_for_cwd(config, cwd) or _project_for_text(config, first_user_message) or "forge"
        status, reason = _infer_rollout_status(rollout, bool(row["archived"]))
        name = row["title"] or first_user_message or thread_id
        created = int(row["created_at"] or now())
        updated = int(row["updated_at"] or created)
        node_id = f"codex:{thread_id}"
        store.upsert_work_item(
            node_id,
            "run",
            f"codex:{name[:80]}",
            status,
            parent_id=parent_id,
            goal=first_user_message,
            next_action=reason if status in {"stale", "unknown"} else "",
            owner="codex",
            source="codex",
            created_at=created,
            updated_at=updated,
        )
        store.add_link(node_id, "codex_thread", thread_id, "Codex thread")
        store.add_link(node_id, "codex_rollout", str(rollout), "rollout JSONL")
        if rollout.exists():
            store.add_evidence(node_id, str(rollout), "conversation", "Codex rollout JSONL")
        store.add_event(node_id, updated, "codex", "thread_status", f"{status}: {reason}")
        for timestamp, message in _user_messages(rollout_events):
            store.add_event(node_id, timestamp, "codex", "user_message", _compact(message))
        for timestamp, message in _assistant_messages(rollout_events):
            store.add_event(node_id, timestamp, "codex", "assistant_message", _compact(message, 1000))
        for timestamp, message in _task_complete_messages(rollout_events):
            store.add_event(node_id, timestamp, "codex", "task_complete", _compact(message, 1200))


def _read_threads(db_path: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """
            select id, title, first_user_message, cwd, rollout_path, created_at, updated_at, archived
            from threads
            order by updated_at desc
            limit 500
            """
        ).fetchall()
    finally:
        conn.close()


def _infer_rollout_status(path: Path, archived: bool) -> tuple[str, str]:
    if archived:
        return "archived", "Codex thread is archived"
    if not path.exists():
        return "unknown", f"rollout file missing: {path}"
    try:
        started = 0
        completed = 0
        last_ts = int(path.stat().st_mtime)
        for line in path.read_text(errors="replace").splitlines()[-2000:]:
            if not line.strip():
                continue
            obj = json.loads(line)
            ts = _parse_ts(obj.get("timestamp")) or last_ts
            last_ts = max(last_ts, ts)
            payload = obj.get("payload", {})
            if obj.get("type") == "event_msg" and payload.get("type") == "task_started":
                started += 1
            if obj.get("type") == "event_msg" and payload.get("type") == "task_complete":
                completed += 1
        if started > completed:
            if now() - last_ts > STALE_SECONDS:
                return "stale", f"task_started without task_complete; no rollout update for {now() - last_ts}s"
            return "running", "latest task_started has no matching task_complete"
        return "idle", "latest recorded turn is complete or no active turn found"
    except Exception as exc:
        return "unknown", f"failed to parse rollout file: {exc}"


def _read_rollout_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                events.append(obj)
    except Exception:
        return []
    return events


def _first_user_message(events: list[dict[str, Any]]) -> str:
    for _, message in _user_messages(events):
        return message
    return ""


def _user_messages(events: list[dict[str, Any]]) -> list[tuple[int, str]]:
    messages: list[tuple[int, str]] = []
    for event in events:
        timestamp = _parse_ts(event.get("timestamp")) or 0
        payload = event.get("payload", {})
        text = _extract_user_message(payload)
        if text:
            messages.append((timestamp, text))
    return messages


def _assistant_messages(events: list[dict[str, Any]]) -> list[tuple[int, str]]:
    messages: list[tuple[int, str]] = []
    for event in events:
        timestamp = _parse_ts(event.get("timestamp")) or 0
        payload = event.get("payload", {})
        text = _extract_assistant_message(payload)
        if text:
            messages.append((timestamp, text))
    return messages


def _task_complete_messages(events: list[dict[str, Any]]) -> list[tuple[int, str]]:
    messages: list[tuple[int, str]] = []
    for event in events:
        if event.get("type") != "event_msg":
            continue
        payload = event.get("payload", {})
        if not isinstance(payload, dict) or payload.get("type") != "task_complete":
            continue
        timestamp = _parse_ts(event.get("timestamp")) or 0
        text = payload.get("last_agent_message")
        if isinstance(text, str) and text.strip():
            messages.append((timestamp, text))
    return messages


def _extract_user_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("type") == "user_message" and isinstance(payload.get("message"), str):
        return payload["message"]
    if payload.get("role") == "user":
        return _content_text(payload.get("content"))
    if payload.get("type") == "message" and payload.get("role") == "user":
        return _content_text(payload.get("content"))
    if payload.get("type") == "response_item":
        inner = payload.get("payload")
        if isinstance(inner, dict) and inner.get("type") == "message" and inner.get("role") == "user":
            return _content_text(inner.get("content"))
    if payload.get("type") == "message":
        return _content_text(payload.get("content")) if payload.get("role") == "user" else ""
    return ""


def _extract_assistant_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("role") == "assistant":
        return _content_text(payload.get("content"))
    if payload.get("type") == "message" and payload.get("role") == "assistant":
        return _content_text(payload.get("content"))
    if payload.get("type") == "response_item":
        inner = payload.get("payload")
        if isinstance(inner, dict) and inner.get("type") == "message" and inner.get("role") == "assistant":
            return _content_text(inner.get("content"))
    return ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("input_text") or item.get("output_text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return ""


def _compact(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _parse_ts(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _project_for_cwd(config: Config, cwd: str) -> str | None:
    if not cwd:
        return None
    path = Path(cwd).resolve()
    best: tuple[int, str] | None = None
    for project_id, project_path in config.projects.items():
        try:
            path.relative_to(project_path)
        except ValueError:
            continue
        depth = len(project_path.parts)
        if best is None or depth > best[0]:
            best = (depth, project_id)
    return best[1] if best else None


def _project_for_text(config: Config, text: str) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for project_id, path in config.projects.items():
        if str(path) in text:
            return project_id
    for project_id, profile in config.project_profiles.items():
        keys = [project_id, *profile.aliases]
        if any(key and key.lower() in lowered for key in keys):
            return project_id
    return None
