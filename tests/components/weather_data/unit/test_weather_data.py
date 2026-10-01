"""Unit tests for the WeatherData component configuration and data retrieval.

The tests in this module focus on the configuration models, the resolution
of the component configuration from static data entities, the timestep
helper and the Brightsky API data retrieval functions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
import requests

from encodapy.components.weather_data.weather_data import (
    WeatherData,
    WeatherDataApiError,
)
from encodapy.components.weather_data.weather_data_config import (
    WeatherDataConfigData,
    WeatherDataOutputData,
)
from encodapy.utils.datapoints import DataPointNumber, DataPointTimestep
from encodapy.utils.units import DataUnits

from tests.components.weather_data.unit import helpers

CURRENT_WEATHER_PAYLOAD = helpers.CURRENT_WEATHER_PAYLOAD
FORECAST_WEATHER_PAYLOAD = helpers.FORECAST_WEATHER_PAYLOAD
ALL_OUTPUTS = helpers.ALL_OUTPUTS
CURRENT_OUTPUTS = helpers.CURRENT_OUTPUTS

_FakeResponse = helpers.FakeResponse
_make_component = helpers.make_component
_patch_requests_get = helpers.patch_requests_get


def test_config_data_defaults_are_set_to_berlin() -> None:
    """The config data model provides Berlin coordinates and intervals."""
    defaults = WeatherDataConfigData().model_dump()

    assert defaults["longitude"]["value"] == pytest.approx(13.4)
    assert defaults["latitude"]["value"] == pytest.approx(52.5)
    assert defaults["forecast_time_range"]["value"] == 1
    assert defaults["forecast_time_range"]["unit"] == DataUnits.DAY
    assert defaults["time_interval_current_weather"]["value"] == 15
    assert defaults["time_interval_current_weather"]["unit"] == DataUnits.MINUTE
    assert defaults["time_interval_forecast_weather"]["value"] == 3
    assert defaults["time_interval_forecast_weather"]["unit"] == DataUnits.HOUR


def test_get_weather_types_maps_all_output_fields() -> None:
    """Every output field is mapped to its api call method."""
    weather_types = WeatherDataOutputData.get_weather_types()

    assert weather_types == {
        "temperature": "current",
        "relative_humidity": "current",
        "pressure_msl": "current",
        "dew_point": "current",
        "solar_60": "current",
        "forecast_temperature": "forecast",
        "forecast_solar": "forecast",
    }


def test_init_resolves_config_data_from_static_entities() -> None:
    """The static data entities override the config data model defaults."""
    component = _make_component()
    assert isinstance(component.config_data, WeatherDataConfigData)
    config = component.config_data.model_dump()
    assert config["longitude"]["value"] == pytest.approx(13.74)
    assert config["latitude"]["value"] == pytest.approx(51.05)
    assert config["forecast_time_range"]["value"] == 2
    assert config["forecast_time_range"]["unit"] == DataUnits.DAY
    assert config["time_interval_current_weather"]["value"] == 15
    assert config["time_interval_current_weather"]["unit"] == DataUnits.MINUTE
    assert config["time_interval_forecast_weather"]["value"] == 3
    assert config["time_interval_forecast_weather"]["unit"] == DataUnits.HOUR


@pytest.mark.parametrize(
    ("outputs", "expected_weather_types"),
    [
        (ALL_OUTPUTS, ["current", "forecast"]),
        (CURRENT_OUTPUTS, ["current"]),
    ],
)
def test_prepare_component_collects_unique_weather_types(
    outputs: dict[str, dict[str, str]], expected_weather_types: list[str]
) -> None:
    """prepare_component collects the api call methods of the configured outputs."""
    component = _make_component(outputs)

    assert component.unique_weather_types == expected_weather_types


def test_get_future_time_adds_minute_timestep() -> None:
    """get_future_time converts a minute timestep into a timedelta."""
    component = _make_component()
    base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = component.get_future_time(
        base_time, DataPointTimestep(value=90, unit=DataUnits.MINUTE)
    )

    assert result == base_time + timedelta(minutes=90)


def test_get_future_time_adds_day_timestep() -> None:
    """get_future_time converts a day timestep into a timedelta."""
    component = _make_component()
    base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    result = component.get_future_time(
        base_time, DataPointTimestep(value=2, unit=DataUnits.DAY)
    )

    assert result == base_time + timedelta(days=2)


def test_get_future_time_raises_for_invalid_timestep() -> None:
    """get_future_time raises a ValueError if the unit cannot be converted."""
    component = _make_component()
    invalid_timestep = DataPointTimestep(value=1, unit=DataUnits.DEGREECELSIUS)

    with pytest.raises(ValueError, match="Invalid time_offset value"):
        component.get_future_time(
            datetime(2026, 1, 1, tzinfo=timezone.utc), invalid_timestep
        )


def test_copy_output_applies_overrides_and_keeps_other_fields() -> None:
    """_copy_output applies overrides and leaves the base output unchanged."""
    base: Any = WeatherDataOutputData(
        temperature=DataPointNumber(value=20.0, unit=DataUnits.DEGREECELSIUS)
    )
    override = DataPointNumber(value=25.0, unit=DataUnits.DEGREECELSIUS)

    copied: Any = WeatherData._copy_output(  # pylint: disable=protected-access
        base, temperature=override
    )
    copied_dump: Any = copied.model_dump()
    base_dump: Any = base.model_dump()

    assert copied_dump["temperature"]["value"] == pytest.approx(25.0)
    assert copied_dump["solar_60"] is None
    assert base_dump["temperature"]["value"] == pytest.approx(20.0)


def test_get_current_weather_data_returns_all_current_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The current weather data is parsed from the brightsky api response."""
    component = _make_component()
    calls = _patch_requests_get(
        monkeypatch, {"/current_weather": _FakeResponse(200, CURRENT_WEATHER_PAYLOAD)}
    )

    current_data = component.get_current_weather_data()

    assert calls[0]["url"].endswith("/current_weather")
    assert calls[0]["timeout"] == pytest.approx(5.0)
    assert calls[0]["params"]["lat"] == pytest.approx(51.05)
    assert calls[0]["params"]["lon"] == pytest.approx(13.74)
    assert current_data.value == {
        "temperature": 21.5,
        "relative_humidity": 45.0,
        "pressure_msl": 1024.2,
        "dew_point": 9.7,
        "solar_60": 2188800.0,
    }


def test_get_current_weather_data_raises_on_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A client error of the brightsky api raises a WeatherDataApiError."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch, {"/current_weather": _FakeResponse(404, {"message": "not found"})}
    )

    with pytest.raises(WeatherDataApiError, match="not found"):
        component.get_current_weather_data()


def test_get_current_weather_data_raises_on_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected status code of the brightsky api raises a WeatherDataApiError."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch, {"/current_weather": _FakeResponse(301, {"message": "moved"})}
    )

    with pytest.raises(WeatherDataApiError, match="moved"):
        component.get_current_weather_data()


def test_get_current_weather_data_returns_empty_dict_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An api timeout results in an empty current weather dict."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch,
        {"/current_weather": _FakeResponse(200, CURRENT_WEATHER_PAYLOAD)},
        error=requests.Timeout("timeout exceeded"),
    )

    current_data = component.get_current_weather_data()

    assert current_data.value == {}


def test_get_current_weather_data_returns_empty_dict_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connection error results in an empty current weather dict."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch,
        {"/current_weather": _FakeResponse(200, CURRENT_WEATHER_PAYLOAD)},
        error=requests.ConnectionError("no route to host"),
    )

    current_data = component.get_current_weather_data()

    assert current_data.value == {}


def test_get_current_weather_data_returns_empty_dict_on_non_json_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-json error body (e.g. a gateway html page) results in an empty dict.

    The error body of the failed request is no valid JSON, so the response
    cannot be parsed and the component falls back to an empty dict.
    """
    component = _make_component()
    _patch_requests_get(
        monkeypatch,
        {"/current_weather": _FakeResponse(502, None, body="<html>Bad Gateway</html>")},
    )

    current_data = component.get_current_weather_data()

    assert current_data.value == {}


def test_get_forecast_weather_data_returns_forecast_dicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The forecast weather data is parsed from the brightsky api response."""
    component = _make_component()
    calls = _patch_requests_get(
        monkeypatch, {"/weather": _FakeResponse(200, FORECAST_WEATHER_PAYLOAD)}
    )

    forecast_data = component.get_forecast_weather_data()

    assert calls[0]["url"].endswith("/weather")
    assert calls[0]["params"]["lat"] == pytest.approx(51.05)
    assert calls[0]["params"]["lon"] == pytest.approx(13.74)
    assert "date" in calls[0]["params"]
    assert "last_date" in calls[0]["params"]
    assert forecast_data.value == {
        "forecast_temperature": {
            "2026-09-29T14:00:00+02:00": 22.3,
            "2026-09-29T15:00:00+02:00": 22.8,
        },
        "forecast_solar": {
            "2026-09-29T14:00:00+02:00": 2318400.0,
            "2026-09-29T15:00:00+02:00": 2250000.0,
        },
    }


def test_get_forecast_weather_data_raises_on_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server error of the brightsky api raises a WeatherDataApiError."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch, {"/weather": _FakeResponse(500, {"message": "server error"})}
    )

    with pytest.raises(WeatherDataApiError, match="server error"):
        component.get_forecast_weather_data()


def test_get_forecast_weather_data_raises_on_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected status code of the brightsky api raises a WeatherDataApiError."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch, {"/weather": _FakeResponse(301, {"message": "moved"})}
    )

    with pytest.raises(WeatherDataApiError, match="moved"):
        component.get_forecast_weather_data()


def test_get_forecast_weather_data_returns_empty_dict_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An api timeout results in an empty forecast weather dict."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch,
        {"/weather": _FakeResponse(200, FORECAST_WEATHER_PAYLOAD)},
        error=requests.Timeout("timeout exceeded"),
    )

    forecast_data = component.get_forecast_weather_data()

    assert forecast_data.value == {}


def test_get_forecast_weather_data_returns_empty_dict_on_non_json_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-json error body (e.g. a gateway html page) results in an empty dict.

    The error body of the failed request is no valid JSON, so the response
    cannot be parsed and the component falls back to an empty dict.
    """
    component = _make_component()
    _patch_requests_get(
        monkeypatch,
        {"/weather": _FakeResponse(502, None, body="<html>Bad Gateway</html>")},
    )

    forecast_data = component.get_forecast_weather_data()

    assert forecast_data.value == {}
