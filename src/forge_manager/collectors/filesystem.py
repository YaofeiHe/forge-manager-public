from __future__ import annotations

from pathlib import Path

from forge_manager.config import Config
from forge_manager.db import Store, now


def collect_filesystem(config: Config, store: Store) -> None:
    store.upsert_work_item("forge", "workspace", "forge", "running", goal="Local forge workspace", source="filesystem")
    for project_id, path in config.projects.items():
        if not path.exists():
            store.upsert_work_item(
                project_id,
                "project",
                project_id,
                "unknown",
                parent_id="forge",
                next_action=f"Configured path does not exist: {path}",
                source="filesystem",
            )
            store.add_event(project_id, now(), "filesystem", "missing_path", f"Missing configured project path: {path}", "warning")
            continue
        updated = int(max((p.stat().st_mtime for p in _iter_project_files(path)), default=path.stat().st_mtime))
        store.upsert_work_item(
            project_id,
            "project",
            project_id,
            "idle",
            parent_id="forge",
            goal=f"Project directory: {path}",
            source="filesystem",
            updated_at=updated,
        )
        store.add_link(project_id, "directory", str(path), "project root")
        store.add_event(project_id, updated, "filesystem", "project_seen", f"Project directory scanned: {path}")


def _iter_project_files(path: Path):
    ignored = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    count = 0
    for item in path.rglob("*"):
        if any(part in ignored for part in item.parts):
            continue
        if item.is_file():
            yield item
            count += 1
            if count >= 400:
                return
