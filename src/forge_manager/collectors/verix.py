from __future__ import annotations

from forge_manager.config import Config
from forge_manager.db import Store, now


def collect_verix(config: Config, store: Store) -> None:
    root = config.root / "verix"
    if not root.exists():
        return
    data_dir = root / ".data"
    found = False
    latest = int(root.stat().st_mtime)
    for candidate in data_dir.rglob("*.json") if data_dir.exists() else []:
        if candidate.name in {"interaction.json", "operation_guide.json"}:
            latest = max(latest, int(candidate.stat().st_mtime))
            node_id = f"verix-artifact:{candidate.relative_to(root)}"
            store.upsert_work_item(node_id, "run", f"verix artifact {candidate.name}", "unknown", parent_id="verix", owner="verix", source="verix", updated_at=int(candidate.stat().st_mtime))
            store.add_evidence(node_id, str(candidate), "artifact", "verix artifact without stable run manifest")
            store.add_link(node_id, "file", str(candidate), candidate.name)
            found = True
    if not found:
        store.add_event(
            "verix",
            latest,
            "verix",
            "adapter_unconfigured",
            "verix adapter could not find a stable run manifest/output directory; use manual link for audit runs",
            "warning",
        )
    else:
        store.add_event(
            "verix",
            latest,
            "verix",
            "adapter_partial",
            "verix artifacts found, but stable audit-run manifest is not configured",
            "warning",
        )
