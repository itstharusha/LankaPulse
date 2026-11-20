from pathlib import Path

SQL_DIR = Path(__file__).parents[1] / "sql"


def test_sql_scripts_exist_in_execution_order() -> None:
    expected = [
        "01_schemas.sql",
        "02_dimensions.sql",
        "03_facts.sql",
        "04_logging_tables.sql",
        "05_load_procedures.sql",
        "06_views_marts.sql",
    ]

    assert [path.name for path in sorted(SQL_DIR.glob("[0-9][0-9]_*.sql"))] == expected


def test_sql_contract_contains_required_objects() -> None:
    scripts = "\n".join(path.read_text(encoding="utf-8") for path in SQL_DIR.glob("*.sql"))

    for schema in ("stg", "dw", "ops"):
        assert f"CREATE SCHEMA {schema}" in scripts
    for table in (
        "dim_date",
        "dim_country",
        "dim_currency",
        "dim_location",
        "fact_fx_rate_daily",
        "fact_weather_daily",
        "fact_tourist_arrivals_monthly",
        "pipeline_watermark",
        "pipeline_run_log",
        "dq_results",
        "sltda_manifest",
    ):
        assert table in scripts
    assert "CREATE OR ALTER PROCEDURE ops.usp_load_fx_rate_daily" in scripts
    assert "CREATE OR ALTER PROCEDURE ops.usp_load_weather_daily" in scripts
    assert "CREATE OR ALTER PROCEDURE ops.usp_load_tourist_arrivals_monthly" in scripts
    assert "CREATE OR ALTER VIEW dw.vw_monthly_tourism_context" in scripts