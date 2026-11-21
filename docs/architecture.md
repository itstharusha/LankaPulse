# Architecture Notes

## Current Local Workflow

```text
Frankfurter/CBSL ─┐
Open-Meteo ────────┼─> scripts/local_backfill.py
SLTDA PDF samples ┘      │
                         ├─> data/raw/ (immutable API payload copies)
                         └─> data/cleansed/ (validated Parquet)
                                  │
                                  └─> scripts/build_local_mart.py
                                           ├─> data/curated/monthly_tourism_context.parquet
                                           ├─> data/curated/monthly_tourism_context.csv
                                           └─> scripts/build_local_report.py
                                                    └─> powerbi/local_report.html
```

Generated `data/` files are local and gitignored. The mart marks arrivals as
incomplete because available sample reports yield only top-ten source-market
rows. It does not represent a complete tourist-arrivals total.

## Planned Azure Deployment

```text
Frankfurter/CBSL + Open-Meteo + SLTDA PDFs
        -> Azure Data Factory
        -> ADLS Gen2: raw -> cleansed -> curated
        -> Azure Functions: Python transforms and DQ checks
        -> Azure SQL star schema
        -> Power BI
```

Raw data is immutable. Invalid rows are written to quarantine with a `reject_reason`.
Azure Data Factory, ADLS Gen2, Azure Functions, Azure SQL, and Power BI Service
remain deployment targets; the local HTML report is a preview and not a `.pbix`.