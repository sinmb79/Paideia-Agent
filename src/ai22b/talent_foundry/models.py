from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TalentIdentity:
    name: str
    gender: str
    major_goal: str
    birth: dict[str, str]
    family: dict[str, Any]
    growth_background: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

