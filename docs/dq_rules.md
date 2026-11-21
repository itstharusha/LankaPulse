# Data Quality Rules

Every rule produces one record for `ops.dq_results` with the run ID, dataset,
severity, row counts, and pass status. `ERROR` rules reject affected rows and
fail the dataset load. `WARN` rules keep the data, but remain visible for alerting
and investigation.

| Rule | Dataset | Severity | Check |
| --- | --- | --- | --- |
| FX01 | FX | ERROR | Rate is present and positive. |
| FX02 | FX | ERROR | No duplicate `(rate_date, quote_currency)` keys. |
| FX03 | FX | WARN | Expected business dates have rates. |
| FX04 | FX | WARN | Day-over-day rate change is within the configured threshold. |
| WX01 | Weather | ERROR | No duplicate `(observation_date, location_key)` keys. |
| WX02 | Weather | ERROR | Minimum temperature is not above maximum temperature. |
| WX03 | Weather | ERROR | Precipitation is present and non-negative. |
| WX04 | Weather | WARN | Expected dates are present for every location. |
| WX05 | Weather | WARN | Temperatures are within the Sri Lankan plausibility range. |
| AR01 | Arrivals | ERROR | Arrivals is a non-negative integer. |
| AR02 | Arrivals | ERROR | No duplicate `(report_month, country_name)` keys. |
| AR03 | Arrivals | ERROR | Country totals reconcile to the stated report total. |
| AR04 | Arrivals | WARN | Country is present in the mapping file. |
| AR05 | Arrivals | WARN | Period-over-period change is within the configured threshold. |
| AR06 | Arrivals | ERROR | Only one report version exists per month. |

Rejected rows carry `reject_reason` and are written under the dataset's
quarantine path. The current SLTDA parser intentionally marks top-ten-only
reports for review because those rows cannot reconcile to the full report total. AR03
fails when a report total is unavailable; an unavailable check is not treated as a pass.
AR05 evaluates month-over-month change per country. WX04 can accept expected
locations and dates to detect missing location/date combinations. Non-finite FX
and required weather values fail their corresponding ERROR checks.