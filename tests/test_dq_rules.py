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
