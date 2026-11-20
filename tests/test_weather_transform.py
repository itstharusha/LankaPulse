import json
from pathlib import Path

from functions.transform_weather.transform import transform_weather


def test_weather_normalizes_sample_payload() -> None:
    payload = json.loads(
        (Path(__file__).parent / "sample_data" / "weather_sample.json").read_text()
    )

    result = transform_weather(payload, "colombo")

    assert result.counts == {"read": 2, "written": 2, "rejected": 0}
    assert list(result.data["location_key"]) == ["colombo", "colombo"]
    assert list(result.data["precip_mm"]) == [2.4, 0.0]


def test_weather_quarantines_invalid_measurements() -> None:
    payload = {
        "daily": {
            "time": ["2026-01-01", "2026-01-02"],
            "temperature_2m_max": [30, 22],
            "temperature_2m_min": [25, 21],
            "precipitation_sum": [-1, 0],
            "wind_speed_10m_max": [10, 10],
        }
    }

    result = transform_weather(payload, "colombo")

    assert len(result.data) == 1
    assert result.rejected.iloc[0]["reject_reason"] == "precipitation must be non-negative"