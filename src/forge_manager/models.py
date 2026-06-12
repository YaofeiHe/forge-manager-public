from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusResult:
    status: str
    reason: str
