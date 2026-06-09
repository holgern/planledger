from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlanledgerError(Exception):
    code: str
    message: str
    remediation: list[str] = field(default_factory=list)
    exit_code: int = 1

    @property
    def kind(self) -> str:
        return self.code

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
        }
        return data
