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
    "coverage_status",
    "report_total",
]

COUNTRY_ALIASES = {
    "Russia": "Russian Federation",
    "Russian Federation": "Russian Federation",
    "United Arab": "United Arab Emirates",
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

FULL_TABLE_HEADING = "INTERNATIONAL TOURIST ARRIVALS BY COUNTRY OF RESIDENCE"
TOP_LEVEL_REGIONS = {
    "AMERICAS": "Americas",
    "AFRICA": "Africa",
    "ASIA & PACIFIC": "Asia & Pacific",
    "EUROPE": "Europe",
    "MIDDLE EAST": "Middle East",
}
REGION_GROUPS = {
    "NORTH AMERICA",
    "CARIBBEAN",
    "& CENTRAL AMERICA",
    "CARIBBEAN & CENTRAL AMERICA",
    "SOUTH AMERICA",
    "NORTH AFRICA",
    "SUB-SAHARAN",
    "SUB-SAHARAN AFRICA",
    "NORTH EAST ASIA",
    "SOUTH EAST ASIA",
    "OCEANIA",
    "SOUTH ASIA",
    "NORTHERN EUROPE",
    "WESTERN EUROPE",
    "CENTRAL / EASTERN EUROPE",
    "SOUTHERN /",
    "MEDITERRANEAN EUROPE",
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
    """Extract a reconciled full-country table or the explicitly partial top ten."""
    report_text = text if text is not None else extract_pdf_text(source_path)
    report_month = _report_month(report_text)
    full_table_warning: str | None = None
    if text is None:
        full_rows, report_total, section_found = _extract_full_country_table(
            source_path, report_month, version
        )
        if section_found and report_total is not None:
            data = pd.DataFrame(full_rows, columns=OUTPUT_COLUMNS)
            parsed_total = int(data["arrivals"].sum()) if not data.empty else 0
            if not data.empty and report_total is not None and parsed_total == report_total:
                data["pct_share"] = (data["arrivals"] / report_total * 100).round(3)
                return TransformResult(
                    data=data,
                    warnings=[f"Full country table reconciled to report total {report_total}"],
                    run_id=run_id,
                    dataset=dataset,
                )
            full_table_warning = (
                "Full country table failed reconciliation: "
                f"parsed={parsed_total}, report_total={report_total}; "
                "using top-ten table only"
            )

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
        numbers = re.findall(r"(?:\d[\d,]*|\([\d.]+\)|[\d.]+|-)", remainder[first_number.start() :])
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
                "coverage_status": "top_ten_partial",
                "report_total": None,
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
    if full_table_warning:
        warnings.append(full_table_warning)
    unmapped = sorted(data.loc[data["region"] == "Unmapped", "country_name"].unique())
    warnings.extend(f"Unmapped country: {country}" for country in unmapped)
    return TransformResult(data=data, warnings=warnings, run_id=run_id, dataset=dataset)


def _extract_full_country_table(
    source_path: Path, report_month: str, version: str
) -> tuple[list[dict[str, object]], int | None, bool]:
    rows: list[dict[str, object]] = []
    active_region = ""
    section_found = False
    report_total: int | None = None
    other_counts: dict[str, int] = {}
    table_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}

    with pdfplumber.open(source_path) as document:
        for page in document.pages:
            page_text = page.extract_text() or ""
            if FULL_TABLE_HEADING in page_text.upper():
                section_found = True
            if not section_found:
                continue

            for table in page.extract_tables(table_settings=table_settings):
                for table_row in table:
                    cells = [
                        re.sub(r"\s+", " ", str(cell)).strip()
                        for cell in table_row
                        if cell and str(cell).strip()
                    ]
                    if not cells:
                        continue
                    first_number = next(
                        (index for index, cell in enumerate(cells) if _number(cell) is not None),
                        len(cells),
                    )
                    label = " ".join(cells[:first_number]).strip()
                    normalized = re.sub(r"\s+", " ", label).upper()
                    amounts = [_number(cell) for cell in cells[first_number:]]
                    total = _air_sea_total(amounts)

                    if normalized in TOP_LEVEL_REGIONS:
                        active_region = TOP_LEVEL_REGIONS[normalized]
                        continue
                    if normalized == "TOTAL":
                        report_total = total
                        continue
                    if not active_region or total is None or not label:
                        continue
                    if normalized in REGION_GROUPS or normalized.startswith("MEDITERRANEAN"):
                        continue
                    if normalized == "EUROPE" and active_region == "Europe":
                        continue
                    if normalized.lower() == "others":
                        other_counts[active_region] = other_counts.get(active_region, 0) + 1
                        label = f"Other market ({active_region}) {other_counts[active_region]}"
                    country = _clean_country(label)
                    rows.append(
                        {
                            "report_month": report_month,
                            "country_name": country,
                            "region": active_region,
                            "arrivals": total,
                            "pct_share": None,
                            "report_version": version,
                            "source_file": source_path.name,
                            "coverage_status": "full_country_reconciled",
                            "report_total": report_total,
                        }
                    )
            if report_total is not None:
                break

    for row in rows:
        row["report_total"] = report_total
    data = pd.DataFrame(rows, columns=OUTPUT_COLUMNS).drop_duplicates(
        ["report_month", "country_name"], keep="last"
    )
    return data.to_dict("records"), report_total, section_found


def _air_sea_total(amounts: list[int | None]) -> int | None:
    for index in range(len(amounts) - 2):
        air, sea, total = amounts[index : index + 3]
        if air is not None and sea is not None and total is not None and air + sea == total:
            return total
    return None


def _report_month(text: str) -> str:
    match = re.search(r"Monthly Tourist Arrivals Report\s+([A-Za-z]+)\s+(\d{4})", text)
    if not match:
        match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+(20\d{2})\b",
            text,
        )
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
