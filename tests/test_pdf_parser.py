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