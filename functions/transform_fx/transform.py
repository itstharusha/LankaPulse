"""Normalize Frankfurter/CBSL exchange-rate responses."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from functions.shared.io import read_json, write_transform_outputs
from functions.shared.results import TransformResult

OUTPUT_COLUMNS = [
    "rate_date",
    "base_currency",
    "quote_currency",
    "rate",
    "provider",
    "ingest_ts",
]


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    raise ValueError("FX payload must be an object or list of objects")


def transform_fx(
    payload: Any,
    ingest_ts: str | None = None,
    run_id: str | None = None,
    dataset: str = "fx",
) -> TransformResult:
    """Return LKR-per-foreign-currency rows and quarantine invalid values."""
    timestamp = ingest_ts or datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for item in _payload_rows(payload):
        date = item.get("date")
        provider = item.get("provider", "CBSL")
        base = str(item.get("base", "LKR")).upper()
        rates = item.get("rates", {})
        if not date or not isinstance(rates, dict):
            rejected.append({"source": item, "reject_reason": "missing date or rates"})
            continue

        for currency, raw_rate in rates.items():
            currency = str(currency).upper()
            try:
                value = float(raw_rate)
            except (TypeError, ValueError):
                rejected.append(
                    {
                        "source": item,
                        "quote_currency": currency,
                        "reject_reason": "rate is not numeric",
                    }
                )
                continue

            if currency == "LKR":
                if base == "LKR":
                    continue
                quote_currency = base
                rate = value
            elif base == "LKR":
                quote_currency = currency
                rate = 1 / value if value else value
            else:
                continue

            row = {
                "rate_date": date,
                "base_currency": "LKR",
                "quote_currency": quote_currency,
                "rate": rate,
                "provider": provider,
                "ingest_ts": timestamp,
            }
            if not quote_currency.isalpha() or len(quote_currency) != 3:
                row["reject_reason"] = "invalid ISO currency code"
                rejected.append(row)
            elif rate <= 0:
                row["reject_reason"] = "rate must be positive"
                rejected.append(row)
            else:
                rows.append(row)

    data = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    rejected_data = pd.DataFrame(rejected)
    if not data.empty:
        duplicate_mask = data.duplicated(["rate_date", "quote_currency"], keep="first")
        duplicate_rows = data.loc[duplicate_mask].copy()
        duplicate_rows["reject_reason"] = "duplicate date and currency"
        rejected_data = pd.concat([rejected_data, duplicate_rows], ignore_index=True)
        data = data.loc[~duplicate_mask].reset_index(drop=True)
    return TransformResult(
        data=data,
        rejected=rejected_data.reset_index(drop=True),
        run_id=run_id,
        dataset=dataset,
    )


def transform_fx_file(
    source_path: Path,
    target_path: Path,
    quarantine_path: Path,
    run_id: str,
    dataset: str = "fx",
) -> TransformResult:
    result = transform_fx(read_json(source_path), run_id=run_id, dataset=dataset)
    write_transform_outputs(result.data, result.rejected, target_path, quarantine_path)
    return result