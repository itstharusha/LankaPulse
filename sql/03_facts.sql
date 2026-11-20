/* Curated facts. Natural keys make reruns idempotent. */
IF OBJECT_ID(N'dw.fact_fx_rate_daily', N'U') IS NULL
BEGIN
    CREATE TABLE dw.fact_fx_rate_daily (
        date_key INT NOT NULL,
        currency_key INT NOT NULL,
        rate_lkr DECIMAL(18,6) NOT NULL,
        source_run_id VARCHAR(40) NULL,
        CONSTRAINT pk_fact_fx_rate_daily PRIMARY KEY (date_key, currency_key),
        CONSTRAINT fk_fact_fx_date FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),
        CONSTRAINT fk_fact_fx_currency FOREIGN KEY (currency_key) REFERENCES dw.dim_currency(currency_key),
        CONSTRAINT ck_fact_fx_rate_positive CHECK (rate_lkr > 0)
    );
END;
GO

IF OBJECT_ID(N'dw.fact_weather_daily', N'U') IS NULL
BEGIN
    CREATE TABLE dw.fact_weather_daily (
        date_key INT NOT NULL,
        location_key INT NOT NULL,
        temp_max_c DECIMAL(5,2) NULL,
        temp_min_c DECIMAL(5,2) NULL,
        precip_mm DECIMAL(7,2) NULL,
        wind_max_kmh DECIMAL(6,2) NULL,
        source_run_id VARCHAR(40) NULL,
        CONSTRAINT pk_fact_weather_daily PRIMARY KEY (date_key, location_key),
        CONSTRAINT fk_fact_weather_date FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),
        CONSTRAINT fk_fact_weather_location FOREIGN KEY (location_key) REFERENCES dw.dim_location(location_key),
        CONSTRAINT ck_fact_weather_precip_nonnegative CHECK (precip_mm IS NULL OR precip_mm >= 0),
        CONSTRAINT ck_fact_weather_temperature_order CHECK (
            temp_min_c IS NULL OR temp_max_c IS NULL OR temp_min_c <= temp_max_c
        )
    );
END;
GO

IF OBJECT_ID(N'dw.fact_tourist_arrivals_monthly', N'U') IS NULL
BEGIN
    CREATE TABLE dw.fact_tourist_arrivals_monthly (
        month_date_key INT NOT NULL,
        country_key INT NOT NULL,
        arrivals INT NOT NULL,
        pct_share DECIMAL(6,3) NULL,
        report_version VARCHAR(30) NOT NULL,
        source_run_id VARCHAR(40) NULL,
        CONSTRAINT pk_fact_tourist_arrivals_monthly PRIMARY KEY (month_date_key, country_key),
        CONSTRAINT fk_fact_arrivals_date FOREIGN KEY (month_date_key) REFERENCES dw.dim_date(date_key),
        CONSTRAINT fk_fact_arrivals_country FOREIGN KEY (country_key) REFERENCES dw.dim_country(country_key),
        CONSTRAINT ck_fact_arrivals_nonnegative CHECK (arrivals >= 0)
    );
END;
GO