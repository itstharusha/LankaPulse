"""Shared result contracts for local and Azure Function transforms."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class TransformResult:
    data: pd.DataFrame
    rejected: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: list[str] = field(default_factory=list)
    run_id: str | None = None
    dataset: str | None = None

    @property
    def counts(self) -> dict[str, int]:
        return {
            "read": len(self.data) + len(self.rejected),
            "written": len(self.data),
            "rejected": len(self.rejected),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.counts,
            "run_id": self.run_id,
            "dataset": self.dataset,
            "warnings": self.warnings,
        }