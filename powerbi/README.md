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

It includes FX history, a rainfall location selector, parsed top-market mix,
and source coverage. The arrivals charts are explicitly partial: they do not
claim full monthly tourist totals.

This HTML preview is not a Power BI `.pbix` file. A native Power BI report and
Azure SQL connection remain a separate deployment deliverable.