from datetime import date

import pandas as pd

from scripts.local_backfill import _date_ranges, _merge_partition


def test_date_ranges_split_inclusive_year_chunks() -> None:
    assert list(_date_ranges(date(2016, 12, 30), date(2017, 1, 2))) == [
        (date(2016, 12, 30), date(2016, 12, 31)),
        (date(2017, 1, 1), date(2017, 1, 2)),
    ]


def test_partition_merge_is_idempotent_and_keeps_range(tmp_path) -> None:
    path = tmp_path / "fx.parquet"
    existing = pd.DataFrame(
        {
            "rate_date": ["2016-12-30", "2017-01-02", "2018-01-02"],
            "quote_currency": ["USD", "USD", "USD"],
            "rate": [300.0, 301.0, 303.0],
        }
    )
    existing.to_parquet(path, index=False)
    update = pd.DataFrame(
        {
            "rate_date": ["2017-01-02"],
            "quote_currency": ["USD"],
            "rate": [302.0],
        }
    )

    result = _merge_partition(
        update,
        path,
        ["rate_date", "quote_currency"],
        "rate_date",
        date(2017, 1, 1),
        date(2017, 12, 31),
    )

    assert result.set_index("rate_date")["rate"].to_dict() == {
        "2016-12-30": 300.0,
        "2017-01-02": 302.0,
        "2018-01-02": 303.0,
    }

    rerun = _merge_partition(
        update,
        path,
        ["rate_date", "quote_currency"],
        "rate_date",
        date(2017, 1, 1),
        date(2017, 12, 31),
    )

    pd.testing.assert_frame_equal(rerun, result)


def test_annual_partition_merge_removes_legacy_out_of_year_rows(tmp_path) -> None:
    partition = tmp_path / "year=2017"
    partition.mkdir()
    path = partition / "fx.parquet"
    pd.DataFrame(
        {
            "rate_date": ["2016-12-30", "2017-01-02", "2018-01-02"],
            "quote_currency": ["USD", "USD", "USD"],
            "rate": [300.0, 301.0, 303.0],
        }
    ).to_parquet(path, index=False)
    update = pd.DataFrame(
        {
            "rate_date": ["2017-01-02"],
            "quote_currency": ["USD"],
            "rate": [302.0],
        }
    )

    result = _merge_partition(
        update,
        path,
        ["rate_date", "quote_currency"],
        "rate_date",
        date(2017, 1, 1),
        date(2017, 12, 31),
    )

    assert result["rate_date"].tolist() == ["2017-01-02"]