"""Download public source history and build local raw/cleansed lake partitions."""

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from functions.ingest_sltda_pdf.parser import parse_sltda_pdf
from functions.shared.config import settings
from functions.shared.io import write_parquet
from functions.transform_fx.transform import transform_fx
from functions.transform_weather.transform import transform_weather

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rates"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
LOCATIONS = {
    "colombo": (6.9271, 79.8612),
    "kandy": (7.2906, 80.6337),
    "galle": (6.0535, 80.2210),
    "nuwara_eliya": (6.9497, 80.7891),
    "sigiriya": (7.9570, 80.7603),
    "arugam_bay": (6.8400, 81.8350),
}
WEATHER_DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"


def _session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "LankaPulse-local-data-project/1.0"})
    return session


def _date_ranges(start: date, end: date):
    for year in range(start.year, end.year + 1):
        range_start = max(start, date(year, 1, 1))
        range_end = min(end, date(year, 12, 31))
        if range_start <= range_end:
            yield range_start, range_end


def _fetch(session: requests.Session, url: str, params: dict[str, Any]) -> requests.Response:
    response = session.get(url, params=params, timeout=(15, 120))
    response.raise_for_status()
    return response


def _raw_path(dataset: str, start: date, end: date, ingest_date: date) -> Path:
    run_stamp = datetime.now(timezone.utc).strftime("%H%M%S%f")
    return (
        settings.raw_root
        / dataset
        / f"ingest_date={ingest_date.isoformat()}"
        / f"{dataset}_{start.isoformat()}_{end.isoformat()}_{run_stamp}.json"
    )


def _merge_partition(
    data: pd.DataFrame,
    path: Path,
    keys: list[str],
    date_column: str,
    range_start: date,
    range_end: date,
) -> pd.DataFrame:
    data_dates = pd.to_datetime(data[date_column]).dt.date
    data = data.loc[data_dates.between(range_start, range_end)]
    if path.exists():
        existing = pd.read_parquet(path)
        year_partition = next(
            (part for part in path.parts if part.startswith("year=")), None
        )
        if year_partition is not None:
            partition_year = int(year_partition.removeprefix("year="))
            existing_dates = pd.to_datetime(existing[date_column]).dt.date
            existing = existing.loc[
                existing_dates.between(date(partition_year, 1, 1), date(partition_year, 12, 31))
            ]
        data = pd.concat([existing, data], ignore_index=True)
    data = data.drop_duplicates(keys, keep="last").reset_index(drop=True)
    write_parquet(data, path)
    return data


def backfill_fx(start: date, end: date, ingest_date: date) -> dict[str, Any]:
    session = _session()
    summary: dict[str, Any] = {
        "dataset": "fx",
        "source_rows": 0,
        "written_rows": 0,
        "rejected_rows": 0,
        "partitions": [],
    }
    for range_start, range_end in _date_ranges(start, end):
        response = _fetch(
            session,
            FRANKFURTER_URL,
            {
                "from": range_start.isoformat(),
                "to": range_end.isoformat(),
                "providers": "CBSL",
                "base": "LKR",
            },
        )
        raw_path = _raw_path("fx", range_start, range_end, ingest_date)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        raw_payload = response.json()
        payload = [
            item
            for item in raw_payload
            if range_start.isoformat() <= item.get("date", "") <= range_end.isoformat()
        ]
        result = transform_fx(
            payload,
            ingest_ts=datetime.now(timezone.utc).isoformat(),
            run_id=f"local-fx-{range_start.year}",
        )
        output_path = (
            settings.cleansed_root
            / "fx"
            / f"year={range_start.year}"
            / f"fx_{range_start.year}.parquet"
        )
        _merge_partition(
            result.data,
            output_path,
            ["rate_date", "quote_currency"],
            "rate_date",
            range_start,
            range_end,
        )
        if not result.rejected.empty:
            reject_path = (
                settings.quarantine_root
                / "fx"
                / f"ingest_date={ingest_date.isoformat()}"
                / f"rejected_{range_start.year}.parquet"
            )
            write_parquet(result.rejected, reject_path)
        source_rows = len(payload)
        summary["source_rows"] += source_rows
        summary["written_rows"] += len(result.data)
        summary["rejected_rows"] += len(result.rejected)
        summary["partitions"].append(str(output_path))
        print(
            f"FX {range_start.year}: source={source_rows:,} "
            f"written={len(result.data):,} rejected={len(result.rejected):,}"
        )
    return summary


def backfill_weather(start: date, end: date, ingest_date: date) -> dict[str, Any]:
    session = _session()
    summary: dict[str, Any] = {
        "dataset": "weather",
        "source_rows": 0,
        "written_rows": 0,
        "rejected_rows": 0,
        "partitions": [],
    }
    for location, (latitude, longitude) in LOCATIONS.items():
        for range_start, range_end in _date_ranges(start, end):
            response = _fetch(
                session,
                OPEN_METEO_URL,
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "start_date": range_start.isoformat(),
                    "end_date": range_end.isoformat(),
                    "daily": WEATHER_DAILY_FIELDS,
                    "timezone": settings.timezone,
                },
            )
            raw_path = (
                settings.raw_root
                / "weather"
                / f"location={location}"
                / f"ingest_date={ingest_date.isoformat()}"
                / f"weather_{range_start.isoformat()}_{range_end.isoformat()}.json"
            )
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            run_stamp = datetime.now(timezone.utc).strftime("%H%M%S%f")
            raw_path = raw_path.with_name(f"{raw_path.stem}_{run_stamp}{raw_path.suffix}")
            raw_path.write_bytes(response.content)
            payload = response.json()
            result = transform_weather(
                payload,
                location,
                ingest_ts=datetime.now(timezone.utc).isoformat(),
                run_id=f"local-weather-{location}-{range_start.year}",
            )
            output_path = (
                settings.cleansed_root
                / "weather"
                / f"location={location}"
                / f"year={range_start.year}"
                / f"weather_{location}_{range_start.year}.parquet"
            )
            _merge_partition(
                result.data,
                output_path,
                ["observation_date", "location_key"],
                "observation_date",
                range_start,
                range_end,
            )
            if not result.rejected.empty:
                reject_path = (
                    settings.quarantine_root
                    / "weather"
                    / f"ingest_date={ingest_date.isoformat()}"
                    / f"rejected_{location}_{range_start.year}.parquet"
                )
                write_parquet(result.rejected, reject_path)
            source_rows = len(payload.get("daily", {}).get("time", []))
            summary["source_rows"] += source_rows
            summary["written_rows"] += len(result.data)
            summary["rejected_rows"] += len(result.rejected)
            summary["partitions"].append(str(output_path))
            print(
                f"Weather {location} {range_start.year}: source={source_rows:,} "
                f"written={len(result.data):,} rejected={len(result.rejected):,}"
            )
    return summary


def parse_local_reports(ingest_date: date) -> dict[str, Any]:
    reports = sorted(Path("tests/sample_data").glob("*.pdf"))
    summary: dict[str, Any] = {
        "dataset": "arrivals",
        "reports": len(reports),
        "parsed_rows": 0,
        "warnings": [],
    }
    frames = []
    for report_path in reports:
        result = parse_sltda_pdf(report_path, run_id=f"local-arrivals-{report_path.stem}")
        frames.append(result.data)
        summary["parsed_rows"] += len(result.data)
        summary["warnings"].extend(
            {"report": report_path.name, "message": warning} for warning in result.warnings
        )
        print(f"Arrivals {report_path.name}: parsed market rows={len(result.data):,}")
    if frames:
        data = pd.concat(frames, ignore_index=True)
        output_path = (
            settings.cleansed_root
            / "arrivals"
            / f"ingest_date={ingest_date.isoformat()}"
            / "arrivals_top_markets.parquet"
        )
        write_parquet(data, output_path)
        summary["output"] = str(output_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fx-start", type=date.fromisoformat, default=date(2011, 1, 1))
    parser.add_argument("--weather-start", type=date.fromisoformat, default=date(2015, 1, 1))
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--weather-lag-days", type=int, default=5)
    parser.add_argument("--skip-fx", action="store_true")
    parser.add_argument("--skip-weather", action="store_true")
    parser.add_argument("--skip-pdfs", action="store_true")
    args = parser.parse_args()

    ingest_date = date.today()
    safe_weather_end = min(args.end_date, date.today() - timedelta(days=args.weather_lag_days))
    summaries = []
    if not args.skip_fx:
        summaries.append(backfill_fx(args.fx_start, args.end_date, ingest_date))
    if not args.skip_weather:
        summaries.append(backfill_weather(args.weather_start, safe_weather_end, ingest_date))
    if not args.skip_pdfs:
        summaries.append(parse_local_reports(ingest_date))

    summary_path = Path("data") / "backfill_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
