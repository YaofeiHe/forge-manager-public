from __future__ import annotations

from pathlib import Path
import subprocess

from forge_manager.config import Config
from forge_manager.db import Store, now, stable_id


def collect_git(config: Config, store: Store) -> None:
    for project_id, path in config.projects.items():
        if not (path / ".git").exists():
            continue
        branch = _git(path, "branch", "--show-current") or "detached"
        dirty = bool(_git(path, "status", "--porcelain"))
        commit = _git(path, "rev-parse", "--short", "HEAD") or "unknown"
        status = "running" if dirty else "idle"
        git_node = f"{project_id}:git"
        store.upsert_work_item(git_node, "branch", f"git:{branch}", status, parent_id=project_id, source="git")
        store.add_link(git_node, "git_branch", f"{path}:{branch}", branch)
        store.add_link(git_node, "commit", commit, "HEAD")
        event_ts = _worktree_mtime(path) if dirty else int(_git(path, "log", "-1", "--format=%ct") or (path / ".git").stat().st_mtime)
        store.add_event(git_node, event_ts, "git", "git_status", f"branch={branch}; dirty={dirty}; head={commit}")
        for worktree in _git_worktrees(path):
            node_id = stable_id(project_id, "worktree", worktree)
            store.upsert_work_item(node_id, "branch", f"worktree:{Path(worktree).name}", "idle", parent_id=project_id, source="git")
            store.add_link(node_id, "git_worktree", worktree, "git worktree")


def _git(path: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=8,
        )
    except Exception:
        return ""
    return proc.stdout.strip()


def _git_worktrees(path: Path) -> list[str]:
    raw = _git(path, "worktree", "list", "--porcelain")
    result = []
    for line in raw.splitlines():
        if line.startswith("worktree "):
            result.append(line.removeprefix("worktree ").strip())
    return result


def _worktree_mtime(path: Path) -> int:
    ignored = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    latest = int(path.stat().st_mtime)
    count = 0
    for item in path.rglob("*"):
        if any(part in ignored for part in item.parts):
            continue
        if item.is_file():
            latest = max(latest, int(item.stat().st_mtime))
            count += 1
            if count >= 600:
                break
    return latest
