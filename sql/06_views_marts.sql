/* Power BI serving view for tourism, FX, and rainfall context. */
CREATE OR ALTER VIEW dw.vw_monthly_tourism_context
AS
WITH monthly_arrivals AS (
    SELECT
        d.full_date AS month_date,
        SUM(f.arrivals) AS total_arrivals,
        SUM(CASE WHEN c.region = 'Asia & Pacific' THEN f.arrivals ELSE 0 END) AS asia_pacific_arrivals,
        SUM(CASE WHEN c.region = 'Europe' THEN f.arrivals ELSE 0 END) AS europe_arrivals,
        SUM(CASE WHEN c.region = 'Americas' THEN f.arrivals ELSE 0 END) AS americas_arrivals
    FROM dw.fact_tourist_arrivals_monthly AS f
    JOIN dw.dim_date AS d ON d.date_key = f.month_date_key
    JOIN dw.dim_country AS c ON c.country_key = f.country_key
    GROUP BY d.full_date
), monthly_fx AS (
    SELECT
        DATEFROMPARTS(d.[year], d.[month], 1) AS month_date,
        AVG(f.rate_lkr) AS average_usd_lkr
    FROM dw.fact_fx_rate_daily AS f
    JOIN dw.dim_date AS d ON d.date_key = f.date_key
    JOIN dw.dim_currency AS c ON c.currency_key = f.currency_key
    WHERE c.currency_code = 'USD'
    GROUP BY DATEFROMPARTS(d.[year], d.[month], 1)
), monthly_weather AS (
    SELECT
        DATEFROMPARTS(d.[year], d.[month], 1) AS month_date,
        SUM(ISNULL(f.precip_mm, 0)) AS total_rainfall_mm,
        AVG(f.temp_max_c) AS average_max_temp_c
    FROM dw.fact_weather_daily AS f
    JOIN dw.dim_date AS d ON d.date_key = f.date_key
    GROUP BY DATEFROMPARTS(d.[year], d.[month], 1)
)
SELECT
    a.month_date,
    a.total_arrivals,
    a.asia_pacific_arrivals,
    a.europe_arrivals,
    a.americas_arrivals,
    x.average_usd_lkr,
    w.total_rainfall_mm,
    w.average_max_temp_c
FROM monthly_arrivals AS a
LEFT JOIN monthly_fx AS x ON x.month_date = a.month_date
LEFT JOIN monthly_weather AS w ON w.month_date = a.month_date;
GO