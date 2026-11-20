/* Reference dimensions used by the curated facts. */
IF OBJECT_ID(N'dw.dim_date', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_date (
        date_key INT NOT NULL CONSTRAINT pk_dim_date PRIMARY KEY,
        full_date DATE NOT NULL CONSTRAINT uq_dim_date_full_date UNIQUE,
        [year] SMALLINT NOT NULL,
        [quarter] TINYINT NOT NULL,
        [month] TINYINT NOT NULL,
        month_name VARCHAR(12) NOT NULL,
        week_of_year TINYINT NOT NULL,
        day_of_week TINYINT NOT NULL,
        is_weekend BIT NOT NULL,
        is_business_day BIT NOT NULL,
        season VARCHAR(20) NULL
    );
END;
GO

IF OBJECT_ID(N'dw.dim_country', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_country (
        country_key INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_dim_country PRIMARY KEY,
        country_name VARCHAR(100) NOT NULL,
        region VARCHAR(50) NULL,
        iso_code CHAR(2) NULL,
        valid_from DATE NULL,
        valid_to DATE NULL,
        is_current BIT NOT NULL CONSTRAINT df_dim_country_current DEFAULT (1),
        CONSTRAINT uq_dim_country_version UNIQUE (country_name, valid_from)
    );
END;
GO

IF OBJECT_ID(N'dw.dim_currency', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_currency (
        currency_key INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_dim_currency PRIMARY KEY,
        currency_code CHAR(3) NOT NULL CONSTRAINT uq_dim_currency_code UNIQUE,
        currency_name VARCHAR(60) NULL
    );
END;
GO

IF OBJECT_ID(N'dw.dim_location', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_location (
        location_key INT IDENTITY(1,1) NOT NULL CONSTRAINT pk_dim_location PRIMARY KEY,
        location_name VARCHAR(60) NOT NULL CONSTRAINT uq_dim_location_name UNIQUE,
        latitude DECIMAL(9,6) NULL,
        longitude DECIMAL(9,6) NULL,
        tourism_zone VARCHAR(40) NULL
    );
END;
GO