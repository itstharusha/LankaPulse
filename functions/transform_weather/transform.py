"""Normalize Open-Meteo historical daily weather responses."""

from pathlib import Path
from typing import Any

import pandas as pd

from functions.shared.io import read_json, write_transform_outputs
from functions.shared.results import TransformResult

OUTPUT_COLUMNS = [
    "observation_date",
    "location_key",
    "temp_max_c",
    "temp_min_c",
    "precip_mm",
    "wind_max_kmh",
]


def transform_weather(
    payload: dict[str, Any],
    location_key: str,
    ingest_ts: str | None = None,
    run_id: str | None = None,
    dataset: str = "weather",
) -> TransformResult:
    """Convert Open-Meteo daily arrays into validated rows."""
    del ingest_ts
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    fields = {
        "temp_max_c": daily.get("temperature_2m_max", []),
        "temp_min_c": daily.get("temperature_2m_min", []),
        "precip_mm": daily.get("precipitation_sum", []),
        "wind_max_kmh": daily.get("wind_speed_10m_max", []),
    }
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, date in enumerate(dates):
        row = {"observation_date": date, "location_key": location_key}
        missing = [name for name, values in fields.items() if index >= len(values)]
        if missing:
            rejected.append({**row, "reject_reason": f"missing fields: {', '.join(missing)}"})
            continue
        row.update({name: values[index] for name, values in fields.items()})
        try:
            row.update({name: float(row[name]) for name in fields})
        except (TypeError, ValueError):
            rejected.append({**row, "reject_reason": "weather value is not numeric"})
            continue
        reason = _validation_reason(row)
        if reason:
            rejected.append({**row, "reject_reason": reason})
        else:
            rows.append(row)

    data = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    rejected_data = pd.DataFrame(rejected)
    if not data.empty:
        duplicate_mask = data.duplicated(["observation_date", "location_key"], keep="first")
        duplicate_rows = data.loc[duplicate_mask].copy()
        duplicate_rows["reject_reason"] = "duplicate date and location"
        rejected_data = pd.concat([rejected_data, duplicate_rows], ignore_index=True)
        data = data.loc[~duplicate_mask].reset_index(drop=True)
    return TransformResult(
        data=data,
        rejected=rejected_data.reset_index(drop=True),
        run_id=run_id,
        dataset=dataset,
    )


def _validation_reason(row: dict[str, Any]) -> str | None:
    if row["precip_mm"] < 0:
        return "precipitation must be non-negative"
    if row["temp_min_c"] > row["temp_max_c"]:
        return "minimum temperature exceeds maximum temperature"
    if not -10 <= row["temp_min_c"] <= 45 or not -10 <= row["temp_max_c"] <= 45:
        return "temperature outside Sri Lanka plausibility range"
    if row["wind_max_kmh"] < 0:
        return "wind speed must be non-negative"
    return None


def transform_weather_file(
    source_path: Path,
    target_path: Path,
    quarantine_path: Path,
    location_key: str,
    run_id: str,
    dataset: str = "weather",
) -> TransformResult:
    result = transform_weather(
        read_json(source_path), location_key, run_id=run_id, dataset=dataset
    )
    write_transform_outputs(result.data, result.rejected, target_path, quarantine_path)
    return result