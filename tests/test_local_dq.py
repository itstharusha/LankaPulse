import pandas as pd

from scripts.run_local_dq import run_local_dq


def _write(root, dataset: str, name: str, frame: pd.DataFrame) -> None:
    path = root / dataset / name
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def test_local_dq_persists_results_and_flags_incomplete_arrivals(tmp_path) -> None:
    cleansed = tmp_path / "cleansed"
    _write(
        cleansed,
        "fx",
        "year=2026/fx.parquet",
        pd.DataFrame(
            {
                "rate_date": ["2026-01-01", "2026-01-02"],
                "quote_currency": ["USD", "USD"],
                "rate": [300.0, 301.0],
            }
        ),
    )
    _write(
        cleansed,
        "weather",
        "year=2026/weather.parquet",
        pd.DataFrame(
            {
                "observation_date": ["2026-01-01", "2026-01-02"],
                "location_key": ["colombo", "colombo"],
                "temp_max_c": [30.0, 31.0],
                "temp_min_c": [24.0, 25.0],
                "precip_mm": [0.0, 1.0],
            }
        ),
    )
    _write(
        cleansed,
        "arrivals",
        "arrivals.parquet",
        pd.DataFrame(
            {
                "report_month": ["2026-01", "2026-02"],
                "country_name": ["India", "India"],
                "region": ["Asia & Pacific", "Asia & Pacific"],
                "arrivals": [100, 120],
                "report_version": ["Final", "Final"],
                "coverage_status": ["full_country_reconciled", "top_ten_partial"],
                "report_total": [100, pd.NA],
            }
        ),
    )
    _write(
        cleansed,
        "arrivals",
        "ingest_date=2026-11-21/arrivals.parquet",
        pd.DataFrame(
            {
                "report_month": ["2026-01", "2026-02"],
                "country_name": ["India", "India"],
                "region": ["Asia & Pacific", "Asia & Pacific"],
                "arrivals": [100, 120],
                "report_version": ["Final", "Final"],
                "coverage_status": ["full_country_reconciled", "top_ten_partial"],
                "report_total": [100, pd.NA],
            }
        ),
    )
    output = tmp_path / "ops"

    results, rejected = run_local_dq(cleansed, output)

    ar03 = results.loc[results["rule_id"].eq("AR03")].iloc[0]
    assert not ar03["passed"]
    assert ar03["severity"] == "ERROR"
    assert rejected.empty
    assert (output / "dq_results.parquet").exists()
    assert (output / "dq_results.csv").exists()
    assert "WX04" in set(results["rule_id"])
