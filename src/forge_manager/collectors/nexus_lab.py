from __future__ import annotations

from pathlib import Path
import json

from forge_manager.config import Config
from forge_manager.db import Store, now, stable_id


def collect_nexus_lab(config: Config, store: Store) -> None:
    root = config.root / "nexus-lab"
    if not root.exists():
        return
    project_id = "nexus-lab"
    runs_dir = root / "runs"
    if runs_dir.exists():
        for run_dir in sorted((p for p in runs_dir.iterdir() if p.is_dir()), reverse=True)[:300]:
            run_id = run_dir.name
            node_id = f"nexus-lab-run:{run_id}"
            status = _run_status(run_dir)
            updated = int(run_dir.stat().st_mtime)
            store.upsert_work_item(node_id, "run", f"nexus-lab run {run_id}", status, parent_id=project_id, owner="nexus-lab", source="nexus_lab", updated_at=updated)
            store.add_link(node_id, "nexus_lab_run", run_id, "nexus-lab run")
            for rel, kind in [
                ("manifest.json", "config"),
                ("artifacts/report.json", "report"),
                ("feedback-bundle.md", "report"),
                ("repair-planning-packet.md", "report"),
                ("interaction.md", "conversation"),
            ]:
                path = run_dir / rel
                if path.exists():
                    store.add_evidence(node_id, str(path), kind, rel)
                    store.add_link(node_id, "file", str(path), rel)
            store.add_event(node_id, updated, "nexus_lab", "run_status", f"{run_id}: {status}")
    cases_dir = root / "cases"
    if cases_dir.exists():
        for case_dir in sorted((p for p in cases_dir.iterdir() if p.is_dir()), reverse=True):
            case_id = f"nexus-lab-case:{case_dir.name}"
            store.upsert_work_item(case_id, "subproject", f"case:{case_dir.name}", "active", parent_id=project_id, owner="nexus-lab", source="nexus_lab", updated_at=int(case_dir.stat().st_mtime))
            store.add_link(case_id, "directory", str(case_dir), "nexus-lab case")
            for path in case_dir.rglob("*"):
                if path.is_file() and path.name in {"lab-goal.md", "acceptance.md", "operation-history.md", "operation-guide.md"}:
                    store.add_evidence(case_id, str(path), "markdown", path.name)


def _run_status(run_dir: Path) -> str:
    report = run_dir / "artifacts" / "report.json"
    if not report.exists():
        return "unknown"
    try:
        data = json.loads(report.read_text(errors="replace"))
    except Exception:
        return "unknown"
    text = json.dumps(data, ensure_ascii=False).lower()
    if "blocked" in text or "阻断" in text:
        return "blocked"
    if "failed" in text or "error" in text:
        return "blocked"
    if "pass" in text or "success" in text or "completed" in text:
        return "done"
    return "idle"
