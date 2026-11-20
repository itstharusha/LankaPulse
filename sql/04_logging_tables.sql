/* Operational tables used by ADF, Functions, and Power BI Data Health. */
IF OBJECT_ID(N'ops.pipeline_watermark', N'U') IS NULL
BEGIN
    CREATE TABLE ops.pipeline_watermark (
        dataset VARCHAR(60) NOT NULL CONSTRAINT pk_pipeline_watermark PRIMARY KEY,
        last_loaded_date DATE NULL,
        updated_ts DATETIME2(3) NOT NULL CONSTRAINT df_pipeline_watermark_updated DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'ops.pipeline_run_log', N'U') IS NULL
BEGIN
    CREATE TABLE ops.pipeline_run_log (
        run_id VARCHAR(40) NOT NULL,
        pipeline_name VARCHAR(100) NOT NULL,
        dataset VARCHAR(60) NOT NULL,
        start_ts DATETIME2(3) NOT NULL,
        end_ts DATETIME2(3) NULL,
        status VARCHAR(20) NOT NULL,
        rows_read INT NULL,
        rows_written INT NULL,
        rows_rejected INT NULL,
        error_message NVARCHAR(2000) NULL,
        CONSTRAINT pk_pipeline_run_log PRIMARY KEY (run_id, dataset)
    );
END;
GO

IF OBJECT_ID(N'ops.dq_results', N'U') IS NULL
BEGIN
    CREATE TABLE ops.dq_results (
        run_id VARCHAR(40) NOT NULL,
        dataset VARCHAR(60) NOT NULL,
        rule_id VARCHAR(40) NOT NULL,
        rule_description VARCHAR(300) NOT NULL,
        severity VARCHAR(10) NOT NULL,
        rows_checked INT NOT NULL,
        rows_failed INT NOT NULL,
        passed BIT NOT NULL,
        checked_ts DATETIME2(3) NOT NULL CONSTRAINT df_dq_results_checked DEFAULT SYSUTCDATETIME(),
        CONSTRAINT pk_dq_results PRIMARY KEY (run_id, dataset, rule_id)
    );
END;
GO

IF OBJECT_ID(N'ops.sltda_manifest', N'U') IS NULL
BEGIN
    CREATE TABLE ops.sltda_manifest (
        report_month DATE NOT NULL,
        url VARCHAR(500) NOT NULL,
        file_name VARCHAR(200) NOT NULL,
        version_label VARCHAR(40) NOT NULL,
        status VARCHAR(20) NOT NULL,
        last_checked_ts DATETIME2(3) NOT NULL CONSTRAINT df_manifest_checked DEFAULT SYSUTCDATETIME(),
        CONSTRAINT pk_sltda_manifest PRIMARY KEY (report_month, version_label)
    );
END;
GO