from __future__ import annotations

from forge_manager.db import Store
from forge_manager.renderers import render_list, render_tree


def structure_report(store: Store, view: str = "tree", active: bool = False) -> str:
    with store.connect() as conn:
        rows = conn.execute("select * from work_items order by name").fetchall()
    if active:
        ids = {row["id"] for row in rows if row["status"] in {"running", "blocked", "planned"}}
        parent = {row["id"]: row["parent_id"] for row in rows}
        stack = list(ids)
        while stack:
            item_id = stack.pop()
            parent_id = parent.get(item_id)
            if parent_id and parent_id not in ids:
                ids.add(parent_id)
                stack.append(parent_id)
        items = [row for row in rows if row["id"] in ids]
    else:
        items = rows
    return render_tree(items) if view == "tree" else render_list(items)
