/* Small idempotent load procedures. Staging tables are populated by Functions/ADF. */
CREATE OR ALTER PROCEDURE ops.usp_upsert_watermark
    @dataset VARCHAR(60),
    @last_loaded_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE ops.pipeline_watermark
    SET last_loaded_date = @last_loaded_date, updated_ts = SYSUTCDATETIME()
    WHERE dataset = @dataset;

    IF @@ROWCOUNT = 0
        INSERT ops.pipeline_watermark (dataset, last_loaded_date)
        VALUES (@dataset, @last_loaded_date);
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_log_pipeline_run
    @run_id VARCHAR(40),
    @pipeline_name VARCHAR(100),
    @dataset VARCHAR(60),
    @start_ts DATETIME2(3),
    @end_ts DATETIME2(3) = NULL,
    @status VARCHAR(20),
    @rows_read INT = NULL,
    @rows_written INT = NULL,
    @rows_rejected INT = NULL,
    @error_message NVARCHAR(2000) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE ops.pipeline_run_log
    SET pipeline_name = @pipeline_name, start_ts = @start_ts, end_ts = @end_ts,
        status = @status, rows_read = @rows_read, rows_written = @rows_written,
        rows_rejected = @rows_rejected, error_message = @error_message
    WHERE run_id = @run_id AND dataset = @dataset;

    IF @@ROWCOUNT = 0
        INSERT ops.pipeline_run_log
            (run_id, pipeline_name, dataset, start_ts, end_ts, status,
             rows_read, rows_written, rows_rejected, error_message)
        VALUES
            (@run_id, @pipeline_name, @dataset, @start_ts, @end_ts, @status,
             @rows_read, @rows_written, @rows_rejected, @error_message);
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_load_fx_rate_daily
    @run_id VARCHAR(40)
AS
BEGIN
    SET NOCOUNT ON;
    MERGE dw.fact_fx_rate_daily AS target
    USING (
        SELECT date_key, currency_key, rate_lkr
        FROM stg.fx_rate_daily
    ) AS source
    ON target.date_key = source.date_key AND target.currency_key = source.currency_key
    WHEN MATCHED THEN UPDATE SET rate_lkr = source.rate_lkr, source_run_id = @run_id
    WHEN NOT MATCHED THEN INSERT (date_key, currency_key, rate_lkr, source_run_id)
        VALUES (source.date_key, source.currency_key, source.rate_lkr, @run_id);
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_load_weather_daily
    @run_id VARCHAR(40)
AS
BEGIN
    SET NOCOUNT ON;
    MERGE dw.fact_weather_daily AS target
    USING (
        SELECT date_key, location_key, temp_max_c, temp_min_c, precip_mm, wind_max_kmh
        FROM stg.weather_daily
    ) AS source
    ON target.date_key = source.date_key AND target.location_key = source.location_key
    WHEN MATCHED THEN UPDATE SET
        temp_max_c = source.temp_max_c, temp_min_c = source.temp_min_c,
        precip_mm = source.precip_mm, wind_max_kmh = source.wind_max_kmh,
        source_run_id = @run_id
    WHEN NOT MATCHED THEN INSERT
        (date_key, location_key, temp_max_c, temp_min_c, precip_mm, wind_max_kmh, source_run_id)
        VALUES
        (source.date_key, source.location_key, source.temp_max_c, source.temp_min_c,
         source.precip_mm, source.wind_max_kmh, @run_id);
END;
GO

CREATE OR ALTER PROCEDURE ops.usp_load_tourist_arrivals_monthly
    @run_id VARCHAR(40)
AS
BEGIN
    SET NOCOUNT ON;
    MERGE dw.fact_tourist_arrivals_monthly AS target
    USING (
        SELECT month_date_key, country_key, arrivals, pct_share, report_version
        FROM stg.tourist_arrivals_monthly
    ) AS source
    ON target.month_date_key = source.month_date_key AND target.country_key = source.country_key
    WHEN MATCHED THEN UPDATE SET
        arrivals = source.arrivals, pct_share = source.pct_share,
        report_version = source.report_version, source_run_id = @run_id
    WHEN NOT MATCHED THEN INSERT
        (month_date_key, country_key, arrivals, pct_share, report_version, source_run_id)
        VALUES
        (source.month_date_key, source.country_key, source.arrivals, source.pct_share,
         source.report_version, @run_id);
END;
GO