"""Run the implemented DQ rules against local cleansed Parquet datasets."""

import argparse
from pathlib import Path

import pandas as pd

from functions.run_dq_checks.checks import DQReport, check_arrivals, check_fx, check_weather
from functions.shared.config import settings
from scripts.local_backfill import LOCATIONS


def _read(root: Path, dataset: str) -> pd.DataFrame:
    files = sorted((root / dataset).rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(path) for path in files], ignore_index=True)


def _combine(reports: list[DQReport]) -> tuple[pd.DataFrame, pd.DataFrame]:
    records = [record for report in reports for record in report.as_records()]
    rejected = [report.rejected for report in reports if not report.rejected.empty]
    dq_results = pd.DataFrame(records)
    if not dq_results.empty:
        dq_results["checked_ts"] = pd.Timestamp.now(tz="UTC")
        dq_results = dq_results.rename(columns={"rule_description": "rule_description"})
    rejected_rows = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    return dq_results, rejected_rows


def run_local_dq(cleansed_root: Path, output_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    fx = _read(cleansed_root, "fx")
    weather = _read(cleansed_root, "weather")
    arrivals = _read(cleansed_root, "arrivals")
    if not arrivals.empty:
        if "coverage_status" not in arrivals:
            arrivals["coverage_status"] = "top_ten_partial"
        else:
            arrivals["coverage_status"] = arrivals["coverage_status"].fillna("top_ten_partial")
        arrivals = arrivals.drop_duplicates().reset_index(drop=True)
    reports = []
    if not fx.empty:
        reports.append(check_fx(fx, "local-backfill-fx"))
    if not weather.empty:
        dates = pd.date_range(
            pd.to_datetime(weather["observation_date"]).min(),
            pd.to_datetime(weather["observation_date"]).max(),
        )
        reports.append(
            check_weather(
                weather,
                "local-backfill-weather",
                expected_dates=dates,
                expected_locations=LOCATIONS.keys(),
            )
        )
    if not arrivals.empty:
        report_totals = None
        if "report_total" in arrivals.columns:
            totals = arrivals.dropna(subset=["report_total"])[
                ["report_month", "report_total"]
            ].drop_duplicates()
            report_totals = {
                str(row.report_month): int(row.report_total) for row in totals.itertuples()
            }
        reports.append(
            check_arrivals(
                arrivals,
                "local-backfill-arrivals",
                report_totals=report_totals,
            )
        )

    dq_results, rejected = _combine(reports)
    output_root.mkdir(parents=True, exist_ok=True)
    dq_results.to_parquet(output_root / "dq_results.parquet", index=False)
    dq_results.to_csv(output_root / "dq_results.csv", index=False)
    if not rejected.empty:
        rejected.to_parquet(output_root / "dq_rejected.parquet", index=False)
    return dq_results, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleansed-root", type=Path, default=settings.cleansed_root)
    parser.add_argument("--output-root", type=Path, default=Path("data/ops"))
    args = parser.parse_args()
    results, rejected = run_local_dq(args.cleansed_root, args.output_root)
    failures = results.loc[(results["severity"] == "ERROR") & ~results["passed"]]
    print(
        f"Wrote {len(results)} DQ results; {len(failures)} ERROR failures; "
        f"{len(rejected)} rejected rows."
    )
    if not failures.empty:
        print(failures[["dataset", "rule_id", "rows_failed"]].to_string(index=False))


if __name__ == "__main__":
    main()
