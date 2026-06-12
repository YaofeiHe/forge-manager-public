from __future__ import annotations

import sqlite3


def render_tree(items: list[sqlite3.Row], root_id: str | None = "forge") -> str:
    children: dict[str | None, list[sqlite3.Row]] = {}
    by_id = {row["id"]: row for row in items}
    for row in items:
        children.setdefault(row["parent_id"], []).append(row)
    for rows in children.values():
        rows.sort(key=lambda r: (r["kind"], r["name"]))
    roots = [by_id[root_id]] if root_id and root_id in by_id else children.get(None, [])
    lines: list[str] = []
    for index, row in enumerate(roots):
        _render_node(row, children, lines, "", index == len(roots) - 1, is_root=True)
    return "\n".join(lines) if lines else "No work items found."


def _render_node(row, children, lines, prefix: str, last: bool, is_root: bool = False) -> None:
    label = f"{row['name']} [{row['status']}]"
    if is_root:
        lines.append(label)
        child_prefix = ""
    else:
        connector = "`- " if last else "|- "
        lines.append(f"{prefix}{connector}{label}")
        child_prefix = prefix + ("   " if last else "|  ")
    rows = children.get(row["id"], [])
    for index, child in enumerate(rows):
        _render_node(child, children, lines, child_prefix, index == len(rows) - 1)
