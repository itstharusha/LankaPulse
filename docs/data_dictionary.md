# Data Dictionary

This document will be expanded during the transformation phase. The initial source contracts are:

| Dataset | Grain | Initial fields |
| --- | --- | --- |
| FX | One currency per date | `rate_date`, `base_currency`, `quote_currency`, `rate`, `provider`, `ingest_ts` |
| Weather | One location per date | `observation_date`, `location_key`, `temp_max_c`, `temp_min_c`, `precip_mm`, `wind_max_kmh` |
| Arrivals | One country per report month | `report_month`, `country_name`, `region`, `arrivals`, `pct_share`, `report_version`, `source_file` |

The FX rate direction will be standardized and documented before the first full load.