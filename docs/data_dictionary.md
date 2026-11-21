# Data Dictionary

## Cleansed Datasets

| Dataset | Grain | Initial fields |
| --- | --- | --- |
| FX | One quote currency per rate date | `rate_date`, `base_currency`, `quote_currency`, `rate`, `provider`, `ingest_ts` |
| Weather | One location per observation date | `observation_date`, `location_key`, `temp_max_c`, `temp_min_c`, `precip_mm`, `wind_max_kmh` |
| Arrivals | One parsed market per report month | `report_month`, `country_name`, `region`, `arrivals`, `pct_share`, `report_version`, `source_file` |

FX `rate` is standardized as Sri Lankan rupees per one unit of foreign currency
(for example, LKR per USD). Source responses with LKR as the base are inverted.

The current SLTDA PDF parser extracts the top-ten source-market table. Its
`arrivals` values must be described as parsed top-market arrivals, not total
monthly arrivals; `pct_share` is currently null when it cannot be robustly
extracted. See [dq_rules.md](dq_rules.md) for incomplete reconciliation policy.

## Curated Local Mart

`monthly_tourism_context` has one row per month and weather location where
weather is available. FX and parsed-arrival monthly metrics are repeated across
those location rows to support a simple location-filterable report.

| Field | Meaning |
| --- | --- |
| `month_date` | First day of the month. |
| `location_key` | Weather location for the row. |
| `parsed_top_market_arrivals` | Sum of parsed top-ten market counts; not full monthly arrivals. |
| `parsed_top_market_*_arrivals` | Parsed-market sums by the parser's region mapping. |
| `parsed_market_count` | Number of parsed country rows in that report month. |
| `arrivals_coverage_status` | `top_ten_source_markets_only` or `no_parsed_market_rows`. |
| `arrivals_is_complete` | Always false until complete country coverage and reconciliation are implemented. |
| `average_usd_lkr` | Monthly mean LKR per USD from daily FX observations. |
| `total_rainfall_mm` | Monthly precipitation sum for the location. |
| `average_*` | Monthly mean of daily weather observations. |
| `weather_observation_days` | Count of daily weather rows contributing to the monthly location metrics. |