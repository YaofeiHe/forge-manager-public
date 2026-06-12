from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo

from forge_manager.db import Store
from forge_manager.renderers import render_list, render_tree


TZ = ZoneInfo("Asia/Shanghai")


def day_bounds(date_text: str | None = None) -> tuple[int, int]:
    date = datetime.now(TZ).date() if date_text is None else datetime.fromisoformat(date_text).date()
    start = datetime.combine(date, dt_time.min, TZ)
    end = datetime.combine(date, dt_time.max, TZ)
    return int(start.timestamp()), int(end.timestamp())


def range_bounds(from_date: str, to_date: str) -> tuple[int, int]:
    start_date = datetime.fromisoformat(from_date).date()
    end_date = datetime.fromisoformat(to_date).date()
    start = datetime.combine(start_date, dt_time.min, TZ)
    end = datetime.combine(end_date, dt_time.max, TZ)
    return int(start.timestamp()), int(end.timestamp())


def rolling_hours_bounds(hours: int) -> tuple[int, int]:
    end = datetime.now(TZ)
    start = end - timedelta(hours=hours)
    return int(start.timestamp()), int(end.timestamp())


def rolling_days_bounds(days: int) -> tuple[int, int]:
    return rolling_hours_bounds(days * 24)


def status_report(store: Store, start_ts: int, end_ts: int, view: str = "list") -> str:
    with store.connect() as conn:
        events = conn.execute(
            """
            select e.*, w.name, w.status, w.kind
            from events e
            left join work_items w on w.id=e.work_item_id
            where e.timestamp between ? and ?
            order by e.timestamp desc
            """,
            (start_ts, end_ts),
        ).fetchall()
        active_ids = {event["work_item_id"] for event in events}
        for event in events:
            _add_ancestors(conn, active_ids, event["work_item_id"])
        if active_ids:
            placeholders = ",".join("?" for _ in active_ids)
            items = conn.execute(f"select * from work_items where id in ({placeholders})", tuple(active_ids)).fetchall()
        else:
            items = []
    lines = [f"Range: {start_ts} - {end_ts}", f"Event count: {len(events)}"]
    if events:
        lines.append("")
        lines.append("Activity:")
        for event in events[:40]:
            lines.append(f"- {event['timestamp']} {event['name'] or event['work_item_id']} [{event['source_type']}]: {event['message']}")
    lines.append("")
    lines.append("Structure:")
    lines.append(render_tree(items) if view == "tree" else render_list(items))
    return "\n".join(lines)


def _add_ancestors(conn, ids: set[str], item_id: str) -> None:
    current = item_id
    while current:
        row = conn.execute("select parent_id from work_items where id=?", (current,)).fetchone()
        if not row or not row["parent_id"]:
            return
        parent = row["parent_id"]
        if parent in ids:
            return
        ids.add(parent)
        current = parent
