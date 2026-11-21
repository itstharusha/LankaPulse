# Data Dictionary

## Cleansed Datasets

| Dataset | Grain | Initial fields |
| --- | --- | --- |
| FX | One quote currency per rate date | `rate_date`, `base_currency`, `quote_currency`, `rate`, `provider`, `ingest_ts` |
| Weather | One location per observation date | `observation_date`, `location_key`, `temp_max_c`, `temp_min_c`, `precip_mm`, `wind_max_kmh` |
| Arrivals | One parsed market per report month | `report_month`, `country_name`, `region`, `arrivals`, `pct_share`, `report_version`, `source_file`, `coverage_status`, `report_total` |

FX `rate` is standardized as Sri Lankan rupees per one unit of foreign currency
(for example, LKR per USD). Source responses with LKR as the base are inverted.

The SLTDA parser uses `coverage_status` to distinguish `top_ten_partial` from
`full_country_reconciled`. It includes an official `report_total` only for a
full-country table that exactly reconciles; partial rows are never represented
as total monthly arrivals. `pct_share` is calculated for reconciled tables and
remains null for partial top-ten extracts. January 2019 is currently the
validated full-country sample; newer layout candidates remain partial when
their extracted table does not reconcile. See [dq_rules.md](dq_rules.md).

## Curated Local Mart

`monthly_tourism_context` has one row per month and weather location where
weather is available. FX and parsed-arrival monthly metrics are repeated across
those location rows to support a simple location-filterable report.

| Field | Meaning |
| --- | --- |
| `month_date` | First day of the month. |
| `location_key` | Weather location for the row. |
| `reported_market_arrivals` | Sum of rows present for the report; interpret with the coverage status. |
| `reported_*_arrivals` | Reported-market sums by region. |
| `reported_market_count` | Number of parsed country/other-market rows in that month. |
| `arrivals_coverage_status` | `full_country_reconciled`, `top_ten_partial`, `mixed_review`, or `no_parsed_market_rows`. |
| `arrivals_is_complete` | True only for a full-country table that reconciles to the official total. |
| `average_usd_lkr` | Monthly mean LKR per USD from daily FX observations. |
| `total_rainfall_mm` | Monthly precipitation sum for the location. |
| `average_*` | Monthly mean of daily weather observations. |
| `weather_observation_days` | Count of daily weather rows contributing to the monthly location metrics. |