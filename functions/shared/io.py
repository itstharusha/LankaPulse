"""Deterministic local file IO used by the transform entry points."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_parquet(data: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, index=False)
    return path


def write_transform_outputs(
    data: pd.DataFrame, rejected: pd.DataFrame, target_path: Path, quarantine_path: Path
) -> None:
    write_parquet(data, target_path)
    if not rejected.empty:
        write_parquet(rejected, quarantine_path)