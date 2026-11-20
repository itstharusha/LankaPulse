/* LankaPulse database namespaces. Safe to run repeatedly. */
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'stg') EXEC(N'CREATE SCHEMA stg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'dw') EXEC(N'CREATE SCHEMA dw');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'ops') EXEC(N'CREATE SCHEMA ops');
GO

IF OBJECT_ID(N'stg.fx_rate_daily', N'U') IS NULL
BEGIN
	CREATE TABLE stg.fx_rate_daily (
		date_key INT NOT NULL,
		currency_key INT NOT NULL,
		rate_lkr DECIMAL(18,6) NOT NULL,
		CONSTRAINT ck_stg_fx_rate_positive CHECK (rate_lkr > 0)
	);
END;
GO

IF OBJECT_ID(N'stg.weather_daily', N'U') IS NULL
BEGIN
	CREATE TABLE stg.weather_daily (
		date_key INT NOT NULL,
		location_key INT NOT NULL,
		temp_max_c DECIMAL(5,2) NULL,
		temp_min_c DECIMAL(5,2) NULL,
		precip_mm DECIMAL(7,2) NULL,
		wind_max_kmh DECIMAL(6,2) NULL
	);
END;
GO

IF OBJECT_ID(N'stg.tourist_arrivals_monthly', N'U') IS NULL
BEGIN
	CREATE TABLE stg.tourist_arrivals_monthly (
		month_date_key INT NOT NULL,
		country_key INT NOT NULL,
		arrivals INT NOT NULL,
		pct_share DECIMAL(6,3) NULL,
		report_version VARCHAR(30) NOT NULL
	);
END;
GO