from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ModelCapability:
    name: str
    provider: str
    local: bool

