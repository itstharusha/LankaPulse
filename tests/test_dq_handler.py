import pandas as pd
import pytest

from functions.run_dq_checks.handler import run_dq_checks_json


def test_dq_handler_returns_adf_friendly_records() -> None:
    result = run_dq_checks_json(
        pd.DataFrame(
            {
                "rate_date": ["2026-01-01"],
                "quote_currency": ["USD"],
                "rate": [309.25],
            }
        ),
        "fx",
        "run-handler",
    )

    assert result["dataset"] == "fx"
    assert result["passed"] is True
    assert len(result["results"]) == 4


def test_dq_handler_rejects_unknown_dataset() -> None:
    with pytest.raises(ValueError, match="Unsupported DQ dataset"):
        run_dq_checks_json(pd.DataFrame(), "unknown", "run-handler")