from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import hashlib
import sqlite3
import time


SCHEMA = """
pragma journal_mode=wal;

create table if not exists work_items (
  id text primary key,
  parent_id text,
  kind text not null,
  name text not null,
  status text not null,
  goal text not null default '',
  next_action text not null default '',
  owner text not null default '',
  source text not null default 'manual',
  created_at integer not null,
  updated_at integer not null,
  completed_at integer
);

create table if not exists events (
  id text primary key,
  work_item_id text not null,
  timestamp integer not null,
  source_type text not null,
  event_type text not null,
  message text not null,
  severity text not null default 'info',
  evidence_id text
);

create table if not exists links (
  id text primary key,
  work_item_id text not null,
  link_type text not null,
  target text not null,
  label text not null default '',
  created_at integer not null
);

create table if not exists evidence (
  id text primary key,
  work_item_id text not null,
  path text not null,
  kind text not null,
  summary text not null default '',
  created_at integer not null
);

create index if not exists idx_work_items_parent on work_items(parent_id);
create index if not exists idx_work_items_status on work_items(status);
create index if not exists idx_events_time on events(timestamp);
create index if not exists idx_links_item on links(work_item_id);
create index if not exists idx_evidence_item on evidence(work_item_id);
"""


def now() -> int:
    return int(time.time())


def stable_id(*parts: object) -> str:
    raw = "\0".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma busy_timeout=30000")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def upsert_work_item(
        self,
        item_id: str,
        kind: str,
        name: str,
        status: str,
        parent_id: str | None = None,
        goal: str = "",
        next_action: str = "",
        owner: str = "",
        source: str = "collector",
        created_at: int | None = None,
        updated_at: int | None = None,
        completed_at: int | None = None,
    ) -> None:
        ts = now()
        created = created_at or ts
        updated = updated_at or ts
        with self.connect() as conn:
            conn.execute(
                """
                insert into work_items
                  (id, parent_id, kind, name, status, goal, next_action, owner, source, created_at, updated_at, completed_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                  parent_id=excluded.parent_id,
                  kind=excluded.kind,
                  name=excluded.name,
                  status=case when work_items.source='manual' and work_items.status='blocked' then work_items.status else excluded.status end,
                  goal=case when excluded.goal='' then work_items.goal else excluded.goal end,
                  next_action=case when work_items.next_action!='' and excluded.next_action='' then work_items.next_action else excluded.next_action end,
                  owner=excluded.owner,
                  source=excluded.source,
                  updated_at=max(work_items.updated_at, excluded.updated_at),
                  completed_at=excluded.completed_at
                """,
                (item_id, parent_id, kind, name, status, goal, next_action, owner, source, created, updated, completed_at),
            )

    def add_event(
        self,
        work_item_id: str,
        timestamp: int,
        source_type: str,
        event_type: str,
        message: str,
        severity: str = "info",
        evidence_id: str | None = None,
    ) -> str:
        event_id = stable_id(work_item_id, timestamp, source_type, event_type, message)
        with self.connect() as conn:
            conn.execute(
                """
                insert or ignore into events
                  (id, work_item_id, timestamp, source_type, event_type, message, severity, evidence_id)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, work_item_id, timestamp, source_type, event_type, message, severity, evidence_id),
            )
        return event_id

    def add_link(self, work_item_id: str, link_type: str, target: str, label: str = "") -> str:
        link_id = stable_id(work_item_id, link_type, target)
        with self.connect() as conn:
            conn.execute(
                """
                insert or ignore into links (id, work_item_id, link_type, target, label, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (link_id, work_item_id, link_type, target, label, now()),
            )
        return link_id

    def mark_work_item(self, item_id: str, status: str | None = None, next_action: str | None = None) -> None:
        with self.connect() as conn:
            row = conn.execute("select id from work_items where id=?", (item_id,)).fetchone()
            if row is None:
                ts = now()
                conn.execute(
                    """
                    insert into work_items
                      (id, parent_id, kind, name, status, goal, next_action, owner, source, created_at, updated_at, completed_at)
                    values (?, null, 'track', ?, ?, '', ?, '', 'manual', ?, ?, null)
                    """,
                    (item_id, item_id, status or "unknown", next_action or "", ts, ts),
                )
                return
            conn.execute(
                """
                update work_items
                set status=coalesce(?, status),
                    next_action=coalesce(?, next_action),
                    source='manual',
                    updated_at=?
                where id=?
                """,
                (status, next_action, now(), item_id),
            )

    def add_evidence(self, work_item_id: str, path: str, kind: str, summary: str = "") -> str:
        evidence_id = stable_id(work_item_id, path, kind)
        with self.connect() as conn:
            conn.execute(
                """
                insert or ignore into evidence (id, work_item_id, path, kind, summary, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (evidence_id, work_item_id, path, kind, summary, now()),
            )
        return evidence_id
