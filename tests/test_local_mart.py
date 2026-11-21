import pandas as pd

from scripts.build_local_mart import build_local_mart


def _write_parquet(root, dataset: str, filename: str, data: pd.DataFrame) -> None:
    path = root / dataset / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, index=False)


def test_local_mart_aggregates_sources_by_month_and_weather_location(tmp_path) -> None:
    cleansed_root = tmp_path / "cleansed"
    _write_parquet(
        cleansed_root,
        "fx",
        "year=2026/fx.parquet",
        pd.DataFrame(
            {
                "rate_date": ["2026-01-01", "2026-01-15", "2026-01-20"],
                "base_currency": ["LKR", "LKR", "LKR"],
                "quote_currency": ["USD", "USD", "EUR"],
                "rate": [300.0, 310.0, 400.0],
            }
        ),
    )
    _write_parquet(
        cleansed_root,
        "weather",
        "location=colombo/weather.parquet",
        pd.DataFrame(
            {
                "observation_date": ["2026-01-01", "2026-01-02"],
                "location_key": ["colombo", "colombo"],
                "temp_max_c": [30.0, 32.0],
                "temp_min_c": [24.0, 26.0],
                "precip_mm": [2.0, 3.0],
                "wind_max_kmh": [10.0, 14.0],
            }
        ),
    )
    _write_parquet(
        cleansed_root,
        "weather",
        "location=galle/weather.parquet",
        pd.DataFrame(
            {
                "observation_date": ["2026-01-01"],
                "location_key": ["galle"],
                "temp_max_c": [31.0],
                "temp_min_c": [25.0],
                "precip_mm": [8.0],
                "wind_max_kmh": [12.0],
            }
        ),
    )
    _write_parquet(
        cleansed_root,
        "arrivals",
        "ingest_date=2026-11-20/arrivals.parquet",
        pd.DataFrame(
            {
                "report_month": ["2026-01"] * 4,
                "country_name": ["India", "United Kingdom", "United States", "Other"],
                "region": ["Asia & Pacific", "Europe", "Americas", "Unmapped"],
                "arrivals": [100, 50, 20, 5],
            }
        ),
    )

    curated_root = tmp_path / "curated"
    mart = build_local_mart(cleansed_root, curated_root)

    assert set(mart["location_key"]) == {"colombo", "galle"}
    colombo = mart.loc[mart["location_key"].eq("colombo")].iloc[0]
    galle = mart.loc[mart["location_key"].eq("galle")].iloc[0]
    assert colombo["average_usd_lkr"] == 305.0
    assert colombo["total_rainfall_mm"] == 5.0
    assert colombo["average_max_temp_c"] == 31.0
    assert colombo["average_min_temp_c"] == 25.0
    assert colombo["average_wind_max_kmh"] == 12.0
    assert colombo["weather_observation_days"] == 2
    assert galle["total_rainfall_mm"] == 8.0
    assert colombo["parsed_top_market_arrivals"] == 175
    assert colombo["parsed_top_market_asia_pacific_arrivals"] == 100
    assert colombo["parsed_top_market_europe_arrivals"] == 50
    assert colombo["parsed_top_market_americas_arrivals"] == 20
    assert colombo["parsed_top_market_unmapped_arrivals"] == 5
    assert colombo["parsed_market_count"] == 4
    assert colombo["arrivals_coverage_status"] == "top_ten_source_markets_only"
    assert not colombo["arrivals_is_complete"]
    assert "total_arrivals" not in mart.columns
    assert (curated_root / "monthly_tourism_context.parquet").exists()
    assert (curated_root / "monthly_tourism_context.csv").exists()
    assert len(pd.read_parquet(curated_root / "monthly_tourism_context.parquet")) == 2
    assert len(pd.read_csv(curated_root / "monthly_tourism_context.csv")) == 2


def test_local_mart_marks_months_without_parsed_arrivals_as_incomplete(tmp_path) -> None:
    cleansed_root = tmp_path / "cleansed"
    _write_parquet(
        cleansed_root,
        "fx",
        "fx.parquet",
        pd.DataFrame(
            {
                "rate_date": ["2026-02-01"],
                "base_currency": ["LKR"],
                "quote_currency": ["USD"],
                "rate": [315.0],
            }
        ),
    )

    mart = build_local_mart(cleansed_root, tmp_path / "curated")

    assert len(mart) == 1
    assert pd.isna(mart.iloc[0]["parsed_top_market_arrivals"])
    assert mart.iloc[0]["arrivals_coverage_status"] == "no_parsed_market_rows"
    assert not mart.iloc[0]["arrivals_is_complete"]
    assert "total_arrivals" not in mart.columns
