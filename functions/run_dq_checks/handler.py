"""Entry point for running dataset DQ checks and returning ADF-friendly records."""

from typing import Any

import pandas as pd

from functions.run_dq_checks.checks import DQReport, check_arrivals, check_fx, check_weather


def run_dq_checks(
    data: pd.DataFrame,
    dataset: str,
    run_id: str,
    **options: Any,
) -> DQReport:
    """Run the selected dataset checks with optional contextual parameters."""
    if dataset == "fx":
        return check_fx(data, run_id, **options)
    if dataset == "weather":
        return check_weather(data, run_id, **options)
    if dataset == "arrivals":
        return check_arrivals(data, run_id, **options)
    raise ValueError(f"Unsupported DQ dataset: {dataset}")


def run_dq_checks_json(
    data: pd.DataFrame, dataset: str, run_id: str, **options: Any
) -> dict[str, object]:
    """Return serializable DQ records and quarantine counts for an orchestration layer."""
    report = run_dq_checks(data, dataset, run_id, **options)
    return {
        "run_id": run_id,
        "dataset": dataset,
        "passed": report.passed,
        "results": report.as_records(),
        "rows_rejected": len(report.rejected),
    }