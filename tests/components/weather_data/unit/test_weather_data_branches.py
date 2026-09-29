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

from encodapy.components.basic_component_config import (
    ComponentIOModel,
    ControllerComponentModel,
)
from encodapy.components.weather_data import weather_data as weather_module
from encodapy.components.weather_data.weather_data import WeatherData
from encodapy.components.weather_data.weather_data_config import (
    WeatherDataInputData,
    WeatherDataOutputData,
)
from encodapy.config.types import AttributeTypes
from encodapy.utils.datapoints import DataPointDict
from encodapy.utils.models import InputDataAttributeModel, StaticDataEntityModel
from encodapy.utils.units import DataUnits

CURRENT_WEATHER_PAYLOAD = {
    "weather": {
        "temperature": 21.5,
        "relative_humidity": 45.0,
        "pressure_msl": 1024.2,
        "dew_point": 9.7,
        "solar_60": 608.0,
    }
}

FORECAST_WEATHER_PAYLOAD = {
    "weather": [
        {
            "timestamp": "2026-09-29T14:00:00+02:00",
            "temperature": 22.3,
            "solar": 644.0,
        },
        {
            "timestamp": "2026-09-29T15:00:00+02:00",
            "temperature": 22.8,
            "solar": 581.0,
        },
    ]
}

ALL_OUTPUTS = {
    "temperature": {"entity": "weatherdata", "attribute": "temperature"},
    "relative_humidity": {"entity": "weatherdata", "attribute": "relative_humidity"},
    "pressure_msl": {"entity": "weatherdata", "attribute": "pressure_msl"},
    "dew_point": {"entity": "weatherdata", "attribute": "dew_point"},
    "solar_60": {"entity": "weatherdata", "attribute": "solar_60"},
    "forecast_temperature": {
        "entity": "weatherdata",
        "attribute": "forecast_temperature",
    },
    "forecast_solar": {"entity": "weatherdata", "attribute": "forecast_solar"},
}

_CURRENT_OUTPUT_KEYS = (
    "temperature",
    "relative_humidity",
    "pressure_msl",
    "dew_point",
    "solar_60",
)

CURRENT_OUTPUTS = {key: ALL_OUTPUTS[key] for key in _CURRENT_OUTPUT_KEYS}

_FORECAST_OUTPUT_KEYS = (
    "forecast_temperature",
    "forecast_solar",
)

FORECAST_OUTPUTS = {key: ALL_OUTPUTS[key] for key in _FORECAST_OUTPUT_KEYS}


class _FakeResponse:  # pylint: disable=too-few-public-methods
    """Minimal stand-in for a requests.Response object."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        """Return the payload of the fake api response."""
        return self._payload


def _static_entities() -> list[StaticDataEntityModel]:
    """Create the static data entities with the component configuration."""

    def _attribute(
        attribute_id: str, value: Any, unit: DataUnits
    ) -> InputDataAttributeModel:
        return InputDataAttributeModel(
            id=attribute_id,
            data=value,
            unit=unit,
            data_type=AttributeTypes.VALUE,
            data_available=True,
            latest_timestamp_input=None,
        )

    return [
        StaticDataEntityModel(
            id="weatherdata",
            attributes=[
                _attribute("longitude", 13.74, DataUnits.DD),
                _attribute("latitude", 51.05, DataUnits.DD),
                _attribute("forecast_time_range", 2, DataUnits.DAY),
                _attribute("time_interval_current_weather", 15, DataUnits.MINUTE),
                _attribute("time_interval_forecast_weather", 3, DataUnits.HOUR),
            ],
        )
    ]


def _component_config(outputs: dict[str, dict[str, str]]) -> ControllerComponentModel:
    """Create a valid component configuration for the WeatherData component."""
    return ControllerComponentModel.model_validate(
        {
            "id": "weatherdata",
            "type": "weather_data",
            "inputs": {},
            "outputs": outputs,
            "config": {
                "longitude": {"entity": "weatherdata", "attribute": "longitude"},
                "latitude": {"entity": "weatherdata", "attribute": "latitude"},
                "forecast_time_range": {
                    "entity": "weatherdata",
                    "attribute": "forecast_time_range",
                },
                "time_interval_current_weather": {
                    "entity": "weatherdata",
                    "attribute": "time_interval_current_weather",
                },
                "time_interval_forecast_weather": {
                    "entity": "weatherdata",
                    "attribute": "time_interval_forecast_weather",
                },
            },
        }
    )


def _make_component(
    outputs: dict[str, dict[str, str]] | None = None,
) -> WeatherData:
    """Create a fully initialized WeatherData component without API calls."""
    return WeatherData(
        config=_component_config(outputs or ALL_OUTPUTS),
        component_id="weatherdata",
        static_data=_static_entities(),
    )


def _bare_component() -> WeatherData:
    """Create a bare WeatherData test instance without running __init__."""
    component = WeatherData.__new__(WeatherData)
    component.unique_weather_types = []
    component.berlin_tz = weather_module.pytz.timezone("Europe/Berlin")
    return component


def _patch_requests_get(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, _FakeResponse],
    error: Exception | None = None,
) -> list[dict[str, Any]]:
    """Replace requests.get of the weather module and record all calls."""
    calls: list[dict[str, Any]] = []

    def fake_get(
        url: str, params: dict | None = None, timeout: float | None = None
    ) -> _FakeResponse:
        calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        if error is not None:
            raise error
        for suffix, response in responses.items():
            if url.endswith(suffix):
                return response
        return _FakeResponse(404, {"message": f"unexpected url: {url}"})

    monkeypatch.setattr(weather_module.requests, "get", fake_get)
    return calls


def _default_responses() -> dict[str, _FakeResponse]:
    """Create the default fake responses for both brightsky api endpoints."""
    return {
        "/current_weather": _FakeResponse(200, CURRENT_WEATHER_PAYLOAD),
        "/weather": _FakeResponse(200, FORECAST_WEATHER_PAYLOAD),
    }


def _elapsed_time(component: WeatherData) -> datetime:
    """Return a time in the past to force a refetch in calculate()."""
    return datetime.now(component.berlin_tz) - timedelta(minutes=1)


def _output_dump(component: WeatherData) -> dict[str, Any]:
    """Return the dumped output data of the component."""
    return component.output_data.model_dump()


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
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["temperature"]["unit"] == DataUnits.DEGREECELSIUS
    assert output["temperature"]["time"] is not None
    assert output["temperature"]["time"].utcoffset() == timedelta(0)
    assert output["relative_humidity"]["value"] == pytest.approx(45.0)
    assert output["pressure_msl"]["value"] == pytest.approx(1024.2)
    assert output["dew_point"]["value"] == pytest.approx(9.7)
    assert output["solar_60"]["value"] == pytest.approx(608.0)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }
    assert output["forecast_solar"]["value"] == {
        "2026-09-29T14:00:00+02:00": 644.0,
        "2026-09-29T15:00:00+02:00": 581.0,
    }


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

    component.next_time_step_current_weather = _elapsed_time(component)
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

    component.next_time_step_forecast_weather = _elapsed_time(component)
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
    component.next_time_step_current_weather = _elapsed_time(component)
    component.next_time_step_forecast_weather = _elapsed_time(component)
    component.calculate()

    assert len(calls) == 4
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
    component.next_time_step_current_weather = _elapsed_time(component)

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
    component.next_time_step_forecast_weather = _elapsed_time(component)

    component.calculate()

    assert len(calls) == 3
    assert calls[-1]["url"].endswith("/weather")
    output = _output_dump(component)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
    }
    assert output["forecast_solar"]["value"] == {
        "2026-09-29T14:00:00+02:00": 644.0,
        "2026-09-29T15:00:00+02:00": 581.0,
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
