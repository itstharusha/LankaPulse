"""Build a local month-by-location tourism context mart from cleansed Parquet."""

import argparse
from pathlib import Path

import pandas as pd

from functions.shared.config import settings

FX_COLUMNS = ["rate_date", "base_currency", "quote_currency", "rate"]
WEATHER_COLUMNS = [
    "observation_date",
    "location_key",
    "temp_max_c",
    "temp_min_c",
    "precip_mm",
    "wind_max_kmh",
]
ARRIVALS_COLUMNS = ["report_month", "country_name", "region", "arrivals"]
REGION_COLUMNS = {
    "Asia & Pacific": "parsed_top_market_asia_pacific_arrivals",
    "Europe": "parsed_top_market_europe_arrivals",
    "Americas": "parsed_top_market_americas_arrivals",
    "Unmapped": "parsed_top_market_unmapped_arrivals",
}
OUTPUT_COLUMNS = [
    "month_date",
    "location_key",
    "parsed_top_market_arrivals",
    *REGION_COLUMNS.values(),
    "parsed_market_count",
    "arrivals_coverage_status",
    "arrivals_is_complete",
    "average_usd_lkr",
    "total_rainfall_mm",
    "average_max_temp_c",
    "average_min_temp_c",
    "average_wind_max_kmh",
    "weather_observation_days",
]


def _read_dataset(root: Path, dataset: str, columns: list[str]) -> pd.DataFrame:
    files = sorted((root / dataset).rglob("*.parquet"))
    if not files:
        return pd.DataFrame(columns=columns)
    return pd.concat(
        [pd.read_parquet(path, columns=columns) for path in files],
        ignore_index=True,
    )


def _month_start(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.to_period("M").dt.to_timestamp()


def _aggregate_fx(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    if data.empty:
        return pd.DataFrame(
            {"month_date": pd.Series(dtype="datetime64[ns]"), "average_usd_lkr": []}
        )
    data = data.loc[
        data["base_currency"].str.upper().eq("LKR") & data["quote_currency"].str.upper().eq("USD")
    ].copy()
    data["rate"] = pd.to_numeric(data["rate"], errors="coerce")
    data["month_date"] = _month_start(data["rate_date"])
    data = data.dropna(subset=["month_date", "rate"])
    data = data.drop_duplicates(["rate_date", "base_currency", "quote_currency"], keep="last")
    return data.groupby("month_date", as_index=False).agg(average_usd_lkr=("rate", "mean"))


def _aggregate_weather(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "month_date",
        "location_key",
        "total_rainfall_mm",
        "average_max_temp_c",
        "average_min_temp_c",
        "average_wind_max_kmh",
        "weather_observation_days",
    ]
    if data.empty:
        return pd.DataFrame(columns=columns)
    data = data.copy()
    data["month_date"] = _month_start(data["observation_date"])
    data = data.dropna(subset=["month_date", "location_key"])
    data = data.drop_duplicates(["observation_date", "location_key"], keep="last")
    for column in ("temp_max_c", "temp_min_c", "precip_mm", "wind_max_kmh"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data.groupby(["month_date", "location_key"], as_index=False).agg(
        total_rainfall_mm=("precip_mm", lambda values: values.sum(min_count=1)),
        average_max_temp_c=("temp_max_c", "mean"),
        average_min_temp_c=("temp_min_c", "mean"),
        average_wind_max_kmh=("wind_max_kmh", "mean"),
        weather_observation_days=("observation_date", "count"),
    )


def _aggregate_arrivals(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "month_date",
        "parsed_top_market_arrivals",
        *REGION_COLUMNS.values(),
        "parsed_market_count",
        "arrivals_coverage_status",
    ]
    if data.empty:
        return pd.DataFrame(columns=columns)
    data = data.copy()
    data["month_date"] = _month_start(data["report_month"])
    data["arrivals"] = pd.to_numeric(data["arrivals"], errors="coerce")
    data["region"] = data["region"].fillna("Unmapped")
    data = data.dropna(subset=["month_date", "arrivals"])
    data = data.drop_duplicates(["month_date", "country_name"], keep="last")
    monthly = data.groupby("month_date").agg(
        parsed_top_market_arrivals=("arrivals", "sum"),
        parsed_market_count=("arrivals", "count"),
    )
    for region, column in REGION_COLUMNS.items():
        regional = data.loc[data["region"].eq(region)].groupby("month_date")["arrivals"].sum()
        monthly[column] = regional.reindex(monthly.index, fill_value=0)
    monthly["arrivals_coverage_status"] = "top_ten_source_markets_only"
    return monthly.reset_index()


def build_local_mart(cleansed_root: Path, curated_root: Path) -> pd.DataFrame:
    """Aggregate cleansed datasets and write the curated Parquet and CSV mart."""
    fx = _aggregate_fx(_read_dataset(cleansed_root, "fx", FX_COLUMNS))
    weather = _aggregate_weather(_read_dataset(cleansed_root, "weather", WEATHER_COLUMNS))
    arrivals = _aggregate_arrivals(_read_dataset(cleansed_root, "arrivals", ARRIVALS_COLUMNS))

    mart = weather.merge(fx, on="month_date", how="outer").merge(
        arrivals, on="month_date", how="outer"
    )
    if mart.empty:
        mart = pd.DataFrame(columns=OUTPUT_COLUMNS)
    else:
        mart["arrivals_coverage_status"] = mart["arrivals_coverage_status"].fillna(
            "no_parsed_market_rows"
        )
        mart["arrivals_is_complete"] = False
        mart = (
            mart.reindex(columns=OUTPUT_COLUMNS)
            .sort_values(["month_date", "location_key"], na_position="last", kind="stable")
            .reset_index(drop=True)
        )

    curated_root.mkdir(parents=True, exist_ok=True)
    mart.to_parquet(curated_root / "monthly_tourism_context.parquet", index=False)
    mart.to_csv(curated_root / "monthly_tourism_context.csv", index=False)
    return mart


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleansed-root", type=Path, default=settings.cleansed_root)
    parser.add_argument("--curated-root", type=Path, default=settings.curated_root)
    args = parser.parse_args()
    mart = build_local_mart(args.cleansed_root, args.curated_root)
    print(
        f"Wrote {len(mart):,} month/location rows to "
        f"{args.curated_root / 'monthly_tourism_context.parquet'} and CSV"
    )


if __name__ == "__main__":
    main()
