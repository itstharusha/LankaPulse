# SQL Assets

SQL scripts will be added in execution order: schemas, dimensions, facts, operational tables, load procedures, and mart views.

The numbered scripts are executed in order:

1. `01_schemas.sql` creates `stg`, `dw`, and `ops` plus the three staging tables.
2. `02_dimensions.sql` creates date, country, currency, and location dimensions.
3. `03_facts.sql` creates the curated fact tables and integrity constraints.
4. `04_logging_tables.sql` creates watermarks, pipeline logs, DQ results, and the SLTDA manifest.
5. `05_load_procedures.sql` creates rerunnable watermark, logging, and fact-load procedures.
6. `06_views_marts.sql` creates the Power BI tourism context view.

Run these scripts against Azure SQL with an account allowed to create schemas, tables,
procedures, and views. The scripts do not contain credentials or source data.