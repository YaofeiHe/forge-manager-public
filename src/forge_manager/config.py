from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_ROOT = Path("<FORGE_ROOT>")
DEFAULT_CODEX_HOME = Path("<LOCAL_PATH_REDACTED>")


@dataclass(frozen=True)
class Config:
    root: Path
    codex_home: Path
    data_dir: Path
    db_path: Path
    projects: dict[str, Path]
    project_profiles: dict[str, "ProjectProfile"]


@dataclass(frozen=True)
class ProjectProfile:
    project_id: str
    path: Path
    kind: str = "project"
    capability: str = ""
    role: str = ""
    aliases: tuple[str, ...] = ()


def load_config(root: Path | None = None) -> Config:
    package_project_root = Path(__file__).resolve().parents[2]
    cwd = Path.cwd()
    project_root = root or (cwd if (cwd / "config" / "projects.toml").exists() else package_project_root)
    config_path = project_root / "config" / "projects.toml"
    data = {}
    if config_path.exists():
        data = tomllib.loads(config_path.read_text())
    forge_root = Path(data.get("root", DEFAULT_ROOT)).expanduser()
    codex_home = Path(data.get("codex_home", DEFAULT_CODEX_HOME)).expanduser()
    projects: dict[str, Path] = {}
    profiles: dict[str, ProjectProfile] = {}
    for project_id, item in data.get("projects", {}).items():
        if isinstance(item, dict):
            rel = item.get("path", project_id)
            capability = str(item.get("capability", ""))
            role = str(item.get("role", ""))
            kind = str(item.get("kind", "project"))
            aliases_raw = item.get("aliases", [])
            aliases = tuple(str(alias) for alias in aliases_raw) if isinstance(aliases_raw, list) else ()
        else:
            rel = str(item)
            capability = ""
            role = ""
            kind = "project"
            aliases = ()
        path = (forge_root / rel).resolve()
        projects[project_id] = path
        profiles[project_id] = ProjectProfile(
            project_id=project_id,
            path=path,
            kind=kind,
            capability=capability,
            role=role,
            aliases=aliases,
        )
    data_dir = project_root / "data"
    return Config(
        root=forge_root,
        codex_home=codex_home,
        data_dir=data_dir,
        db_path=data_dir / "forge-manager.sqlite",
        projects=projects,
        project_profiles=profiles,
    )
