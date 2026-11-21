"""Dataset-level data-quality checks for local runs and Azure Functions."""

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DQResult:
    run_id: str
    dataset: str
    rule_id: str
    rule_description: str
    severity: str
    rows_checked: int
    rows_failed: int
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "dataset": self.dataset,
            "rule_id": self.rule_id,
            "rule_description": self.rule_description,
            "severity": self.severity,
            "rows_checked": self.rows_checked,
            "rows_failed": self.rows_failed,
            "passed": self.passed,
        }


@dataclass
class DQReport:
    results: list[DQResult] = field(default_factory=list)
    rejected: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def passed(self) -> bool:
        return all(result.passed or result.severity != "ERROR" for result in self.results)

    def as_records(self) -> list[dict[str, object]]:
        return [result.as_dict() for result in self.results]


def check_fx(
    data: pd.DataFrame,
    run_id: str,
    expected_dates: Iterable[str] | None = None,
    change_threshold: float = 0.05,
) -> DQReport:
    report = DQReport()
    rate = pd.to_numeric(data["rate"], errors="coerce")
    _append_row_rule(
        report,
        data,
        run_id,
        "fx",
        "FX01",
        "rate is positive and not null",
        "ERROR",
        ~np.isfinite(rate) | (rate <= 0),
    )
    duplicate_mask = data.duplicated(["rate_date", "quote_currency"], keep=False)
    _append_row_rule(
        report,
        data,
        run_id,
        "fx",
        "FX02",
        "no duplicate date and currency",
        "ERROR",
        duplicate_mask,
    )
    if expected_dates is not None:
        expected = set(pd.to_datetime(list(expected_dates)).strftime("%Y-%m-%d"))
        actual = set(pd.to_datetime(data["rate_date"]).dt.strftime("%Y-%m-%d"))
        missing = len(expected - actual)
        _append_result(
            report,
            run_id,
            "fx",
            "FX03",
            "business-day rates are present",
            "WARN",
            len(expected),
            missing,
        )
    else:
        _append_result(
            report, run_id, "fx", "FX03", "business-day rates are present", "WARN", len(data), 0
        )
    changes = _percentage_change_mask(data, ["quote_currency"], "rate", change_threshold)
    _append_row_rule(
        report,
        data,
        run_id,
        "fx",
        "FX04",
        "day-over-day change is within threshold",
        "WARN",
        changes,
    )
    return report


def check_weather(
    data: pd.DataFrame,
    run_id: str,
    expected_dates: Iterable[str] | None = None,
    plausible_range: tuple[float, float] = (-10, 45),
    expected_locations: Iterable[str] | None = None,
) -> DQReport:
    report = DQReport()
    duplicate_mask = data.duplicated(["observation_date", "location_key"], keep=False)
    _append_row_rule(
        report,
        data,
        run_id,
        "weather",
        "WX01",
        "no duplicate date and location",
        "ERROR",
        duplicate_mask,
    )
    temp_min = pd.to_numeric(data["temp_min_c"], errors="coerce")
    temp_max = pd.to_numeric(data["temp_max_c"], errors="coerce")
    order_mask = ~np.isfinite(temp_min) | ~np.isfinite(temp_max) | (temp_min > temp_max)
    _append_row_rule(
        report,
        data,
        run_id,
        "weather",
        "WX02",
        "minimum temperature is not above maximum",
        "ERROR",
        order_mask,
    )
    precipitation = pd.to_numeric(data["precip_mm"], errors="coerce")
    precip_mask = ~np.isfinite(precipitation) | (precipitation < 0)
    _append_row_rule(
        report,
        data,
        run_id,
        "weather",
        "WX03",
        "precipitation is non-negative",
        "ERROR",
        precip_mask,
    )
    if expected_dates is not None or expected_locations is not None:
        locations = (
            set(expected_locations)
            if expected_locations is not None
            else set(data["location_key"].dropna())
        )
        missing = 0
        if expected_dates is not None:
            expected = set(pd.to_datetime(list(expected_dates)).strftime("%Y-%m-%d"))
            actual = {
                (location, date)
                for location, date in zip(
                    data["location_key"],
                    pd.to_datetime(data["observation_date"]).dt.strftime("%Y-%m-%d"),
                )
            }
            missing = sum(
                (location, date) not in actual for location in locations for date in expected
            )
            rows_checked = len(locations) * len(expected)
        else:
            actual_locations = set(data["location_key"].dropna())
            missing = len(locations - actual_locations)
            rows_checked = len(locations)
        _append_result(
            report,
            run_id,
            "weather",
            "WX04",
            "loaded dates are complete per location",
            "WARN",
            rows_checked,
            missing,
        )
    else:
        _append_result(
            report,
            run_id,
            "weather",
            "WX04",
            "loaded dates are complete per location",
            "WARN",
            len(data),
            0,
        )
    low, high = plausible_range
    range_mask = (temp_min < low) | (temp_max > high)
    _append_row_rule(
        report,
        data,
        run_id,
        "weather",
        "WX05",
        "temperatures are plausible for Sri Lanka",
        "WARN",
        range_mask,
    )
    return report


def check_arrivals(
    data: pd.DataFrame,
    run_id: str,
    report_totals: dict[str, int] | None = None,
    change_threshold: float = 1.0,
) -> DQReport:
    report = DQReport()
    numeric = pd.to_numeric(data["arrivals"], errors="coerce")
    integer_mask = numeric.isna() | (numeric < 0) | (numeric % 1 != 0)
    _append_row_rule(
        report,
        data,
        run_id,
        "arrivals",
        "AR01",
        "arrivals is a non-negative integer",
        "ERROR",
        integer_mask,
    )
    duplicate_mask = data.duplicated(["report_month", "country_name"], keep=False)
    _append_row_rule(
        report,
        data,
        run_id,
        "arrivals",
        "AR02",
        "no duplicate month and country",
        "ERROR",
        duplicate_mask,
    )
    report_months = set(data["report_month"].astype(str))
    expected_totals = report_totals or {}
    failed = sum(
        month not in expected_totals
        or int(data.loc[data["report_month"].astype(str).eq(month), "arrivals"].sum())
        != expected_totals[month]
        for month in report_months
    )
    _append_result(
        report,
        run_id,
        "arrivals",
        "AR03",
        "country totals reconcile to report total",
        "ERROR",
        len(report_months),
        failed,
    )
    unknown_mask = data["region"].eq("Unmapped") | data["region"].isna()
    _append_row_rule(
        report,
        data,
        run_id,
        "arrivals",
        "AR04",
        "country is present in the region mapping",
        "WARN",
        unknown_mask,
    )
    change_mask = _arrivals_percentage_change_mask(data, change_threshold)
    _append_row_rule(
        report,
        data,
        run_id,
        "arrivals",
        "AR05",
        "period-over-period change is within threshold",
        "WARN",
        change_mask,
    )
    version_mask = data.groupby("report_month")["report_version"].transform("nunique") > 1
    _append_row_rule(
        report,
        data,
        run_id,
        "arrivals",
        "AR06",
        "one report version per month",
        "ERROR",
        version_mask,
    )
    return report


def _append_row_rule(
    report: DQReport,
    data: pd.DataFrame,
    run_id: str,
    dataset: str,
    rule_id: str,
    description: str,
    severity: str,
    mask: pd.Series,
) -> None:
    failed = mask.fillna(True).astype(bool)
    if severity == "ERROR" and failed.any():
        rejected = data.loc[failed].copy()
        rejected["reject_reason"] = rule_id
        report.rejected = pd.concat([report.rejected, rejected], ignore_index=True)
    _append_result(
        report, run_id, dataset, rule_id, description, severity, len(data), int(failed.sum())
    )


def _append_result(
    report: DQReport,
    run_id: str,
    dataset: str,
    rule_id: str,
    description: str,
    severity: str,
    rows_checked: int,
    rows_failed: int,
) -> None:
    report.results.append(
        DQResult(
            run_id=run_id,
            dataset=dataset,
            rule_id=rule_id,
            rule_description=description,
            severity=severity,
            rows_checked=rows_checked,
            rows_failed=rows_failed,
            passed=rows_failed == 0,
        )
    )


def _percentage_change_mask(
    data: pd.DataFrame, group_columns: list[str], value_column: str, threshold: float
) -> pd.Series:
    if data.empty:
        return pd.Series(dtype=bool)
    ordered = data.assign(_date=pd.to_datetime(data["rate_date"])).sort_values(
        _date_columns(group_columns)
    )
    previous = ordered.groupby(group_columns)[value_column].shift(1)
    change = (ordered[value_column] - previous).abs() / previous.abs()
    mask = change.gt(threshold).fillna(False)
    return mask.reindex(data.index, fill_value=False)


def _arrivals_percentage_change_mask(data: pd.DataFrame, threshold: float) -> pd.Series:
    if data.empty:
        return pd.Series(dtype=bool)
    ordered = data.assign(_month=pd.to_datetime(data["report_month"]))
    ordered = ordered.sort_values(["country_name", "_month"])
    arrivals = pd.to_numeric(ordered["arrivals"], errors="coerce")
    previous = arrivals.groupby(ordered["country_name"]).shift(1)
    prior_zero = previous.eq(0)
    change = (arrivals - previous).abs().div(previous.abs().where(~prior_zero))
    change = change.mask(prior_zero & arrivals.eq(0), 0)
    change = change.mask(prior_zero & arrivals.ne(0), np.inf)
    return change.gt(threshold).reindex(data.index, fill_value=False)


def _date_columns(group_columns: list[str]) -> list[str]:
    return [*group_columns, "_date"]
