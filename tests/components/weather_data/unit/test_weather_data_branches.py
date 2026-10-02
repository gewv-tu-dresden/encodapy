"""Unit tests for defensive branches of the WeatherData component.

The tests in this module cover the calculate() control flow (api call
intervals, error fallbacks) and the prepare_component() validation paths.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
import requests
from pydantic import ValidationError

from encodapy.components.basic_component_config import ComponentIOModel
from encodapy.components.weather_data import weather_data as weather_module
from encodapy.components.weather_data.weather_data import WeatherData
from encodapy.components.weather_data.weather_data_config import (
    WeatherDataInputData,
    WeatherDataOutputData,
)
from encodapy.utils.datapoints import DataPointDict
from encodapy.utils.units import DataUnits

from tests.components.weather_data.unit import helpers

CURRENT_WEATHER_PAYLOAD = helpers.CURRENT_WEATHER_PAYLOAD
FORECAST_WEATHER_PAYLOAD = helpers.FORECAST_WEATHER_PAYLOAD
ALL_OUTPUTS = helpers.ALL_OUTPUTS
CURRENT_OUTPUTS = helpers.CURRENT_OUTPUTS
FORECAST_OUTPUTS = helpers.FORECAST_OUTPUTS

_FakeResponse = helpers.FakeResponse
_make_component = helpers.make_component
_patch_requests_get = helpers.patch_requests_get
_default_responses = helpers.default_responses
_elapsed_time = helpers.elapsed_time
_output_dump = helpers.output_dump


def _bare_component() -> WeatherData:
    """Create a bare WeatherData test instance without running __init__."""
    component = WeatherData.__new__(WeatherData)
    component.unique_weather_types = []
    return component


def test_prepare_component_raises_without_io_model() -> None:
    """prepare_component raises a ValueError if no io model is set."""
    component = _bare_component()
    component.io_model = None

    with pytest.raises(ValueError, match="No output configuration found"):
        component.prepare_component()


def test_prepare_component_raises_without_configured_outputs() -> None:
    """prepare_component raises a ValueError if no output field is configured."""
    component = _bare_component()
    component.io_model = ComponentIOModel(
        input=WeatherDataInputData(), output=WeatherDataOutputData()
    )

    with pytest.raises(ValueError, match="No weather outputs configured"):
        component.prepare_component()


def test_calculate_sets_all_outputs_on_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first calculate() call fetches both api endpoints and sets all outputs."""
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())

    component.calculate()

    assert len(calls) == 2
    output = _output_dump(component)
    current_data = CURRENT_WEATHER_PAYLOAD.get("weather", {})
    assert output["temperature"]["value"] == pytest.approx(
        current_data.get("temperature") - 273.15
    )
    assert output["temperature"]["unit"] == DataUnits.DEGREECELSIUS
    assert output["temperature"]["time"] is not None
    assert output["temperature"]["time"].utcoffset() == timedelta(0)
    assert output["relative_humidity"]["value"] == pytest.approx(
        current_data.get("relative_humidity")
    )
    assert output["relative_humidity"]["unit"] == DataUnits.PERCENT
    assert output["pressure_msl"]["value"] == pytest.approx(
        current_data.get("pressure_msl")
    )
    assert output["pressure_msl"]["unit"] == DataUnits.PAL
    assert output["dew_point"]["value"] == pytest.approx(
        current_data.get("dew_point") - 273.15
    )
    assert output["dew_point"]["unit"] == DataUnits.DEGREECELSIUS
    assert output["solar_60"]["value"] == pytest.approx(current_data.get("solar_60"))
    assert output["solar_60"]["unit"] == DataUnits.B13
    forecast_temperature_temps = {
        item["timestamp"]: round(item["temperature"] - 273.15, 3)
        for item in FORECAST_WEATHER_PAYLOAD.get("weather", [])
    }
    forecast_solar_values = {
        item["timestamp"]: item["solar"]
        for item in FORECAST_WEATHER_PAYLOAD.get("weather", [])
    }
    assert output["forecast_temperature"]["value"] == forecast_temperature_temps
    assert output["forecast_temperature"]["unit"] == DataUnits.DEGREECELSIUS
    assert output["forecast_solar"]["value"] == forecast_solar_values
    assert output["forecast_solar"]["unit"] == DataUnits.B13


def test_calculate_reuses_last_data_within_time_intervals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() within the configured intervals triggers no new api calls."""
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())

    component.calculate()
    component.calculate()

    assert len(calls) == 2
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)


def test_calculate_refetches_current_data_after_interval_elapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An elapsed current weather interval triggers a refetch of the current data."""
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())
    component.calculate()

    component.next_time_step_current_weather = _elapsed_time()
    component.calculate()

    assert len(calls) == 3
    assert calls[-1]["url"].endswith("/current_weather")


def test_calculate_refetches_forecast_data_after_interval_elapsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An elapsed forecast interval triggers a refetch of the forecast data."""
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())
    component.calculate()

    component.next_time_step_forecast_weather = _elapsed_time()
    component.calculate()

    assert len(calls) == 3
    assert calls[-1]["url"].endswith("/weather")


def test_calculate_keeps_last_output_when_api_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() keeps the last output when both api calls fail with an error."""
    component = _make_component()
    responses = _default_responses()
    calls = _patch_requests_get(monkeypatch, responses)
    component.calculate()

    responses["/current_weather"] = _FakeResponse(500, {"message": "server error"})
    responses["/weather"] = _FakeResponse(500, {"message": "server error"})
    component.next_time_step_current_weather = _elapsed_time()
    component.next_time_step_forecast_weather = _elapsed_time()
    component.calculate()

    assert len(calls) == 4
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }


def test_calculate_keeps_last_output_on_non_json_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() keeps the last output on a non-json error body.

    A gateway error page (no valid JSON) must not crash the calculation,
    but fall back to the last known output data.
    """
    component = _make_component()
    responses = _default_responses()
    calls = _patch_requests_get(monkeypatch, responses)
    component.calculate()

    responses["/current_weather"] = _FakeResponse(
        502, None, body="<html>Bad Gateway</html>"
    )
    responses["/weather"] = _FakeResponse(502, None, body="<html>Bad Gateway</html>")
    component.next_time_step_current_weather = _elapsed_time()
    component.next_time_step_forecast_weather = _elapsed_time()
    component.calculate()

    assert len(calls) == 4
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }


def test_calculate_retries_failed_api_calls_on_next_timestep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed api call does not advance the retry time step.

    The next time step is only advanced after a successful api call,
    so the next calculate() call retries the failed request instead of
    waiting for the full configured interval.
    """
    component = _make_component()
    responses = _default_responses()
    calls = _patch_requests_get(monkeypatch, responses)
    component.calculate()

    responses["/current_weather"] = _FakeResponse(500, {"message": "server error"})
    responses["/weather"] = _FakeResponse(500, {"message": "server error"})
    component.next_time_step_current_weather = _elapsed_time()
    component.next_time_step_forecast_weather = _elapsed_time()
    component.calculate()

    assert len(calls) == 4
    assert component.next_time_step_current_weather < datetime.now(
        weather_module.WEATHER_DATA_TZ
    )
    assert component.next_time_step_forecast_weather < datetime.now(
        weather_module.WEATHER_DATA_TZ
    )

    responses["/current_weather"] = _FakeResponse(200, CURRENT_WEATHER_PAYLOAD)
    responses["/weather"] = _FakeResponse(200, FORECAST_WEATHER_PAYLOAD)
    component.calculate()

    assert len(calls) == 6
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }


def test_calculate_keeps_empty_output_when_api_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() keeps the (empty) last output when the api is unreachable."""
    component = _make_component()
    _patch_requests_get(
        monkeypatch, _default_responses(), error=requests.ConnectionError("offline")
    )

    component.calculate()

    output = _output_dump(component)
    assert output["temperature"] is None
    assert output["forecast_temperature"] is None


def test_calculate_keeps_last_output_on_incomplete_current_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() keeps the last output when the current data fails validation.

    An incomplete current weather payload (missing attributes resolve to None)
    raises a ValidationError inside calculate(), which falls back to the
    last known output.
    """
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())
    component.calculate()

    incomplete_data = DataPointDict(value={"temperature": 21.5})

    def incomplete_get_current_weather_data() -> DataPointDict:
        return incomplete_data

    monkeypatch.setattr(
        component, "get_current_weather_data", incomplete_get_current_weather_data
    )
    component.next_time_step_current_weather = _elapsed_time()

    component.calculate()

    assert len(calls) == 2
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)


def test_calculate_keeps_last_output_on_invalid_forecast_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """calculate() keeps the last forecast output when the data fails validation.

    The first DataPointDict construction happens in get_forecast_weather_data()
    (the return value) and must stay valid, so the fake raises a ValidationError
    for the construction inside calculate() only.
    """
    component = _make_component()
    calls = _patch_requests_get(monkeypatch, _default_responses())
    component.calculate()

    real_datapoint_dict = weather_module.DataPointDict
    construction_count = {"count": 0}

    def invalid_datapoint_dict(**kwargs: Any) -> DataPointDict:
        construction_count["count"] += 1
        if construction_count["count"] > 1:
            raise ValidationError.from_exception_data(
                "DataPointDict", [{"type": "missing", "loc": ("value",), "input": {}}]
            )
        return real_datapoint_dict(**kwargs)

    monkeypatch.setattr(weather_module, "DataPointDict", invalid_datapoint_dict)
    component.next_time_step_forecast_weather = _elapsed_time()

    component.calculate()

    assert len(calls) == 3
    assert calls[-1]["url"].endswith("/weather")
    output = _output_dump(component)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }
    assert output["forecast_solar"]["value"] == {
        "2026-09-29T14:00:00+02:00": 250000,
        "2026-09-29T15:00:00+02:00": 460000,
    }


def test_calculate_with_current_outputs_only_skips_forecast_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configuration with only current outputs triggers no forecast api call."""
    component = _make_component(CURRENT_OUTPUTS)
    calls = _patch_requests_get(monkeypatch, _default_responses())

    component.calculate()

    assert len(calls) == 1
    assert calls[0]["url"].endswith("/current_weather")
    output = _output_dump(component)
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["forecast_temperature"] is None


def test_calculate_with_forecast_outputs_only_skips_current_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configuration with only forecast outputs triggers no current api call."""
    component = _make_component(FORECAST_OUTPUTS)
    calls = _patch_requests_get(monkeypatch, _default_responses())

    component.calculate()

    assert len(calls) == 1
    assert calls[0]["url"].endswith("/weather")
    output = _output_dump(component)
    assert output["temperature"] is None
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }
