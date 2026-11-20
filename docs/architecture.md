# Architecture Notes

The planned flow is:

```text
Frankfurter/CBSL + Open-Meteo + SLTDA PDFs
        -> Azure Data Factory
        -> ADLS Gen2: raw -> cleansed -> curated
        -> Azure Functions: Python transforms and DQ checks
        -> Azure SQL star schema
        -> Power BI
```

Raw data is immutable. Invalid rows are written to quarantine with a `reject_reason`. Azure resources will be provisioned only after local parsing and transformation work is complete.