from __future__ import annotations

import sqlite3


def render_list(items: list[sqlite3.Row], root_id: str | None = "forge") -> str:
    children: dict[str | None, list[sqlite3.Row]] = {}
    by_id = {row["id"]: row for row in items}
    for row in items:
        children.setdefault(row["parent_id"], []).append(row)
    for rows in children.values():
        rows.sort(key=lambda r: (r["kind"], r["name"]))
    roots = [by_id[root_id]] if root_id and root_id in by_id else children.get(None, [])
    lines: list[str] = []
    for index, row in enumerate(roots, start=1):
        _render_node(row, children, lines, [index], 0)
    return "\n".join(lines) if lines else "No work items found."


def _render_node(row, children, lines, numbering: list[int], level: int) -> None:
    indent = "   " * level
    number = ".".join(str(n) for n in numbering)
    lines.append(f"{indent}{number}. {row['name']} [{row['status']}]")
    details = [
        ("type", row["kind"]),
        ("goal", row["goal"]),
        ("next", row["next_action"]),
        ("owner", row["owner"]),
    ]
    for key, value in details:
        if value:
            lines.append(f"{indent}   {key}: {value}")
    rows = children.get(row["id"], [])
    for index, child in enumerate(rows, start=1):
        _render_node(child, children, lines, [*numbering, index], level + 1)
