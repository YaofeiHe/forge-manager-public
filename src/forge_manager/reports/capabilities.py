from __future__ import annotations

from forge_manager.config import Config
from forge_manager.db import Store


def capabilities_report(config: Config, store: Store, view: str = "list") -> str:
    with store.connect() as conn:
        rows = conn.execute("select * from work_items where kind='project' order by name").fetchall()

    lines = ["forge children"]
    if not rows:
        lines.append("No projects found.")
        return "\n".join(lines)

    for row in rows:
        profile = config.project_profiles.get(row["id"])
        capability = profile.capability if profile else ""
        role = profile.role if profile else ""
        summary = capability or role or row["goal"] or "能力说明待补充"
        lines.append(f"- {row['name']} [{row['status']}]: {summary}")
    return "\n".join(lines)
