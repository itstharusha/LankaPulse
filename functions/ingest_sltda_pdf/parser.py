"""Defensive parser for SLTDA monthly report text layouts."""

import re
from pathlib import Path

import pandas as pd
import pdfplumber

from functions.shared.io import write_transform_outputs
from functions.shared.results import TransformResult

OUTPUT_COLUMNS = [
    "report_month",
    "country_name",
    "region",
    "arrivals",
    "pct_share",
    "report_version",
    "source_file",
]

COUNTRY_ALIASES = {
    "Russia": "Russian Federation",
    "Russian Federation": "Russian Federation",
}

COUNTRY_REGIONS = {
    "Australia": "Asia & Pacific",
    "Bangladesh": "Asia & Pacific",
    "China": "Asia & Pacific",
    "India": "Asia & Pacific",
    "Japan": "Asia & Pacific",
    "Maldives": "Asia & Pacific",
    "Malaysia": "Asia & Pacific",
    "Pakistan": "Asia & Pacific",
    "Singapore": "Asia & Pacific",
    "Canada": "Americas",
    "United States": "Americas",
    "France": "Europe",
    "Germany": "Europe",
    "Italy": "Europe",
    "Netherlands": "Europe",
    "Russian Federation": "Europe",
    "Spain": "Europe",
    "Switzerland": "Europe",
    "Turkey": "Europe",
    "United Kingdom": "Europe",
}


def _country_aliases() -> dict[str, str]:
    mapping_path = Path(__file__).parents[1] / "shared" / "country_mapping.csv"
    mapping = pd.read_csv(mapping_path)
    return dict(zip(mapping["source_name"], mapping["canonical_name"], strict=True))


def extract_pdf_text(source_path: Path) -> str:
    with pdfplumber.open(source_path) as document:
        return "\n".join(page.extract_text() or "" for page in document.pages)


def parse_sltda_pdf(
    source_path: Path,
    version: str = "Final",
    text: str | None = None,
    run_id: str | None = None,
    dataset: str = "arrivals",
) -> TransformResult:
    """Extract the report's top-ten source-market table.

    Current SLTDA reports expose a top-ten table rather than a complete country
    table. The result is therefore marked for review until a full reconciliation
    source is available.
    """
    report_text = text if text is not None else extract_pdf_text(source_path)
    report_month = _report_month(report_text)
    rows: list[dict[str, object]] = []
    in_market_table = False
    for line in report_text.splitlines():
        if "Table 2. Top ten source markets" in line:
            in_market_table = True
            continue
        if in_market_table and line.startswith("Chart 2:"):
            in_market_table = False
        if not in_market_table:
            continue
        match = re.match(r"^\s*(\d{1,2})\s+(.+)$", line)
        if not match:
            continue
        remainder = match.group(2)
        first_number = re.search(r"(?:\d[\d,]*|-)(?=\s|$)", remainder)
        if not first_number:
            continue
        country = _clean_country(remainder[: first_number.start()])
        numbers = re.findall(
            r"(?:\d[\d,]*|\([\d.]+\)|[\d.]+|-)", remainder[first_number.start() :]
        )
        if len(numbers) < 3:
            continue
        if country.lower() in {"rank", "country of residence"}:
            continue
        total = _number(numbers[2])
        if total is None:
            continue
        rows.append(
            {
                "report_month": report_month,
                "country_name": country,
                "region": COUNTRY_REGIONS.get(country, "Unmapped"),
                "arrivals": total,
                "pct_share": None,
                "report_version": version,
                "source_file": source_path.name,
            }
        )

    data = pd.DataFrame(rows, columns=OUTPUT_COLUMNS).drop_duplicates(
        ["report_month", "country_name"], keep="last"
    )
    warnings = []
    if data.empty:
        warnings.append("No source-market rows matched the known report layout")
    else:
        warnings.append(
            "Report contains top-ten source markets; full reconciliation requires all markets"
        )
    unmapped = sorted(data.loc[data["region"] == "Unmapped", "country_name"].unique())
    warnings.extend(f"Unmapped country: {country}" for country in unmapped)
    return TransformResult(data=data, warnings=warnings, run_id=run_id, dataset=dataset)


def _report_month(text: str) -> str:
    match = re.search(r"Monthly Tourist Arrivals Report\s+([A-Za-z]+)\s+(\d{4})", text)
    if not match:
        raise ValueError("Could not find report month in SLTDA PDF")
    return pd.to_datetime(f"{match.group(1)} {match.group(2)}").strftime("%Y-%m")


def _clean_country(value: str) -> str:
    value = re.sub(r"\s+", " ", value.replace("Singap ore", "Singapore")).strip()
    return _country_aliases().get(value, COUNTRY_ALIASES.get(value, value))


def _number(value: str) -> int | None:
    value = value.replace(",", "")
    if value == "-":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_sltda_pdf_file(
    source_path: Path,
    target_path: Path,
    quarantine_path: Path,
    run_id: str,
    version: str = "Final",
    dataset: str = "arrivals",
) -> TransformResult:
    result = parse_sltda_pdf(source_path, version, run_id=run_id, dataset=dataset)
    write_transform_outputs(result.data, result.rejected, target_path, quarantine_path)
    return result