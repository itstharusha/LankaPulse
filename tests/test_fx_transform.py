import json
from pathlib import Path

import pytest

from functions.transform_fx.transform import transform_fx


def test_fx_normalizes_foreign_base_to_lkr() -> None:
    payload = json.loads((Path(__file__).parent / "sample_data" / "fx_sample.json").read_text())

    result = transform_fx(payload, ingest_ts="2026-01-03T00:00:00+00:00")

    assert result.counts == {"read": 1, "written": 1, "rejected": 0}
    assert result.data.iloc[0]["base_currency"] == "LKR"
    assert result.data.iloc[0]["quote_currency"] == "USD"
    assert result.data.iloc[0]["rate"] == 309.25


def test_fx_quarantines_invalid_and_duplicate_rows() -> None:
    payload = [
        {"date": "2026-01-01", "base": "USD", "rates": {"LKR": 300}},
        {"date": "2026-01-01", "base": "USD", "rates": {"LKR": -1}},
        {"date": "2026-01-01", "base": "USD", "rates": {"LKR": 300}},
    ]

    result = transform_fx(payload)

    assert len(result.data) == 1
    assert len(result.rejected) == 2
    assert set(result.rejected["reject_reason"]) == {
        "rate must be positive",
        "duplicate date and currency",
    }


def test_fx_handles_frankfurter_flat_records_and_lkr_base() -> None:
    result = transform_fx(
        [
            {"date": "2026-01-02", "base": "LKR", "quote": "USD", "rate": 0.00323}
        ]
    )

    assert result.data.iloc[0]["quote_currency"] == "USD"
    assert result.data.iloc[0]["rate"] == pytest.approx(1 / 0.00323)