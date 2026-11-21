import pandas as pd

from functions.run_dq_checks.checks import check_arrivals, check_fx, check_weather


def test_fx_rules_pass_for_valid_rows() -> None:
    data = pd.DataFrame(
        {
            "rate_date": ["2026-01-01", "2026-01-02"],
            "quote_currency": ["USD", "USD"],
            "rate": [309.25, 310.0],
        }
    )

    report = check_fx(data, "run-1", expected_dates=["2026-01-01", "2026-01-02"])

    assert {result.rule_id for result in report.results} == {"FX01", "FX02", "FX03", "FX04"}
    assert report.passed
    assert report.rejected.empty


def test_fx01_rejects_non_finite_rates() -> None:
    data = pd.DataFrame(
        {
            "rate_date": ["2026-01-01", "2026-01-02"],
            "quote_currency": ["USD", "EUR"],
            "rate": [float("nan"), float("inf")],
        }
    )

    report = check_fx(data, "run-fx-non-finite")

    fx01 = next(result for result in report.results if result.rule_id == "FX01")
    assert not fx01.passed
    assert fx01.rows_failed == 2
    assert set(report.rejected["reject_reason"]) == {"FX01"}


def test_weather_errors_are_quarantined() -> None:
    data = pd.DataFrame(
        {
            "observation_date": ["2026-01-01"],
            "location_key": ["colombo"],
            "temp_max_c": [25.0],
            "temp_min_c": [30.0],
            "precip_mm": [-1.0],
        }
    )

    report = check_weather(data, "run-2")

    assert not report.passed
    assert {result.rule_id for result in report.results if not result.passed} == {"WX02", "WX03"}
    assert set(report.rejected["reject_reason"]) == {"WX02", "WX03"}


def test_weather_rejects_non_finite_numeric_values() -> None:
    data = pd.DataFrame(
        {
            "observation_date": ["2026-01-01", "2026-01-02"],
            "location_key": ["colombo", "galle"],
            "temp_max_c": [25.0, float("inf")],
            "temp_min_c": [float("nan"), 20.0],
            "precip_mm": [float("nan"), float("inf")],
        }
    )

    report = check_weather(data, "run-weather-non-finite")

    failed = {result.rule_id: result.rows_failed for result in report.results}
    assert failed["WX02"] == 2
    assert failed["WX03"] == 2
    assert set(report.rejected["reject_reason"]) == {"WX02", "WX03"}


def test_wx04_counts_missing_dates_and_expected_locations() -> None:
    data = pd.DataFrame(
        {
            "observation_date": ["2026-01-01", "2026-01-01"],
            "location_key": ["colombo", "galle"],
            "temp_max_c": [25.0, 27.0],
            "temp_min_c": [20.0, 22.0],
            "precip_mm": [0.0, 0.0],
        }
    )

    report = check_weather(
        data,
        "run-wx04",
        expected_dates=["2026-01-01", "2026-01-02"],
        expected_locations=["colombo", "galle", "kandy"],
    )

    wx04 = next(result for result in report.results if result.rule_id == "WX04")
    assert wx04.rows_checked == 6
    assert wx04.rows_failed == 4
    assert not wx04.passed


def test_arrivals_detects_unmapped_country_and_duplicate_version() -> None:
    data = pd.DataFrame(
        {
            "report_month": ["2026-05", "2026-05"],
            "country_name": ["Exampleland", "Exampleland"],
            "region": ["Unmapped", "Unmapped"],
            "arrivals": [10, 10],
            "report_version": ["Final", "Updated"],
        }
    )

    report = check_arrivals(data, "run-3", report_totals={"2026-05": 20})

    failed = {result.rule_id for result in report.results if not result.passed}
    assert {"AR02", "AR06"}.issubset(failed)
    assert any(result.rule_id == "AR04" and not result.passed for result in report.results)


def test_ar03_fails_when_report_totals_are_unavailable() -> None:
    data = pd.DataFrame(
        {
            "report_month": ["2026-05"],
            "country_name": ["Exampleland"],
            "region": ["Asia"],
            "arrivals": [10],
            "report_version": ["Final"],
        }
    )

    report = check_arrivals(data, "run-ar03")

    ar03 = next(result for result in report.results if result.rule_id == "AR03")
    assert not ar03.passed
    assert ar03.severity == "ERROR"
    assert ar03.rows_failed == 1
    assert not report.passed


def test_ar03_fails_for_each_month_missing_a_report_total() -> None:
    data = pd.DataFrame(
        {
            "report_month": ["2026-01", "2026-02"],
            "country_name": ["A", "A"],
            "region": ["Asia", "Asia"],
            "arrivals": [10, 12],
            "report_version": ["Final", "Final"],
        }
    )

    report = check_arrivals(data, "run-ar03-missing-month", report_totals={"2026-01": 10})

    ar03 = next(result for result in report.results if result.rule_id == "AR03")
    assert ar03.rows_checked == 2
    assert ar03.rows_failed == 1


def test_ar05_checks_sorted_country_period_changes_with_zero_baselines() -> None:
    data = pd.DataFrame(
        {
            "report_month": [
                "2026-03",
                "2026-01",
                "2026-02",
                "2026-03",
                "2026-01",
                "2026-02",
            ],
            "country_name": ["A", "A", "A", "B", "B", "B"],
            "region": ["Asia"] * 6,
            "arrivals": [220, 100, 110, 1, 0, 0],
            "report_version": ["Final"] * 6,
        }
    )

    report = check_arrivals(
        data,
        "run-ar05",
        report_totals={"2026-01": 100, "2026-02": 110, "2026-03": 221},
        change_threshold=0.5,
    )

    ar05 = next(result for result in report.results if result.rule_id == "AR05")
    assert ar05.rows_checked == 6
    assert ar05.rows_failed == 2
    assert not ar05.passed
