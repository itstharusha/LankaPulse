import pandas as pd

from scripts.build_local_report import build_local_report


def test_local_report_is_offline_and_states_arrivals_coverage(tmp_path) -> None:
    mart_path = tmp_path / "monthly_tourism_context.parquet"
    pd.DataFrame(
        {
            "month_date": ["2026-05-01", "2026-05-01"],
            "location_key": ["colombo", "galle"],
            "parsed_top_market_arrivals": [100, 100],
            "parsed_top_market_asia_pacific_arrivals": [70, 70],
            "parsed_top_market_europe_arrivals": [20, 20],
            "parsed_top_market_americas_arrivals": [10, 10],
            "parsed_top_market_unmapped_arrivals": [0, 0],
            "parsed_market_count": [10, 10],
            "arrivals_coverage_status": [
                "top_ten_source_markets_only",
                "top_ten_source_markets_only",
            ],
            "arrivals_is_complete": [False, False],
            "average_usd_lkr": [300.0, 300.0],
            "total_rainfall_mm": [50.0, 90.0],
            "average_max_temp_c": [30.0, 29.0],
            "average_min_temp_c": [24.0, 23.0],
            "average_wind_max_kmh": [12.0, 13.0],
            "weather_observation_days": [31, 31],
        }
    ).to_parquet(mart_path, index=False)
    output_path = tmp_path / "local_report.html"
    dq_path = tmp_path / "dq_results.parquet"
    pd.DataFrame(
        {
            "dataset": ["arrivals"],
            "rule_id": ["AR03"],
            "severity": ["ERROR"],
            "rows_failed": [1],
            "passed": [False],
        }
    ).to_parquet(dq_path, index=False)

    build_local_report(mart_path, output_path, dq_path)

    html = output_path.read_text(encoding="utf-8")
    assert "Tourism &amp; Economy" in html
    assert "top-ten source-market tables only" in html
    assert "not total tourist arrivals" in html
    assert "Data health" in html
    assert "AR03" in html
    assert "Plotly.newPlot" in html
    assert '<script src="https://cdn.plot.ly/plotly-' not in html
