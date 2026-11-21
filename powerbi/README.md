# Reporting Assets

## Local report preview

The generated [local_report.html](local_report.html) is an offline-capable
interactive preview built from `data/curated/monthly_tourism_context.parquet`.
Regenerate it from the repository root with:

```powershell
py -m scripts.build_local_mart
py -m scripts.run_local_dq
py -m scripts.build_local_report
```

It includes FX history, a rainfall location selector, reported-market mix,
and source coverage. January 2019 is a complete country table reconciled to the
official monthly total; recent top-ten extracts remain explicitly partial and
are never presented as full monthly totals.

This HTML preview is not a Power BI `.pbix` file. A native Power BI report and
Azure SQL connection remain a separate deployment deliverable.