from __future__ import annotations

from forge_manager.db import Store
from forge_manager.renderers import render_list, render_tree


def project_report(store: Store, project_id: str, view: str = "list") -> str:
    with store.connect() as conn:
        rows = conn.execute("select * from work_items").fetchall()
        ids = _descendant_ids(rows, project_id)
        if not ids:
            return f"Project/work item not found: {project_id}"
        placeholders = ",".join("?" for _ in ids)
        items = conn.execute(f"select * from work_items where id in ({placeholders}) order by name", tuple(ids)).fetchall()
        events = conn.execute(
            f"select * from events where work_item_id in ({placeholders}) order by timestamp desc limit 20",
            tuple(ids),
        ).fetchall()
        links = conn.execute(
            f"select * from links where work_item_id in ({placeholders}) order by created_at desc limit 20",
            tuple(ids),
        ).fetchall()
    body = render_tree(items, root_id=project_id) if view == "tree" else render_list(items, root_id=project_id)
    lines = [body]
    if events:
        lines.extend(["", "Recent events:"])
        for event in events:
            lines.append(f"- {event['timestamp']} {event['source_type']}/{event['event_type']}: {event['message']}")
    if links:
        lines.extend(["", "Links:"])
        for link in links:
            lines.append(_format_link(link))
    return "\n".join(lines)


def _format_link(link) -> str:
    link_type = link["link_type"]
    target = link["target"]
    label = link["label"]
    if link_type == "codex_thread":
        return f"- {link_type}: [{target}](codex://threads/{target}) ({label})"
    return f"- {link_type}: {target} ({label})"


def _descendant_ids(rows, root_id: str) -> set[str]:
    children: dict[str | None, list[str]] = {}
    all_ids = set()
    for row in rows:
        all_ids.add(row["id"])
        children.setdefault(row["parent_id"], []).append(row["id"])
    if root_id not in all_ids:
        return set()
    result = {root_id}
    stack = [root_id]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child not in result:
                result.add(child)
                stack.append(child)
    return result
