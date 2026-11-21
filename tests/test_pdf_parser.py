from pathlib import Path

import pytest

from functions.ingest_sltda_pdf.parser import parse_sltda_pdf

SAMPLE_DIR = Path(__file__).parent / "sample_data"
REPORTS = [
    ("MonthlyTouritsArrivalsReport-May-2026-Final-1.pdf", "2026-05"),
    ("Monthly_Tourits_Arrivals_Report-October-2025-Final.pdf", "2025-10"),
    ("MonthlyTouritsArrivalsReport-June-2026-Final-Updated_1.pdf", "2026-06"),
]


@pytest.mark.parametrize(("filename", "report_month"), REPORTS)
def test_pdf_parser_extracts_current_report_layout(filename: str, report_month: str) -> None:
    result = parse_sltda_pdf(SAMPLE_DIR / filename)

    assert result.counts == {"read": 10, "written": 10, "rejected": 0}
    assert set(result.data["report_month"]) == {report_month}
    assert result.data["arrivals"].min() > 0
    assert any("full reconciliation" in warning for warning in result.warnings)


def test_pdf_parser_normalizes_russia_alias() -> None:
    result = parse_sltda_pdf(SAMPLE_DIR / "MonthlyTouritsArrivalsReport-May-2026-Final-1.pdf")

    assert "Russian Federation" in set(result.data["country_name"])
    assert "Russia" not in set(result.data["country_name"])


def test_2019_full_country_table_reconciles_to_report_total() -> None:
    result = parse_sltda_pdf(SAMPLE_DIR / "sltda_2019_01_full_country.pdf")

    assert len(result.data) == 87
    assert set(result.data["report_month"]) == {"2019-01"}
    assert int(result.data["arrivals"].sum()) == 244_239
    assert set(result.data["report_total"]) == {244_239}
    assert set(result.data["coverage_status"]) == {"full_country_reconciled"}
    assert result.data["country_name"].str.startswith("Other market").any()
    assert result.data["pct_share"].notna().all()
    assert any("reconciled to report total 244239" in warning for warning in result.warnings)
