"""Shared test helpers for the WeatherData component unit tests.

Provides fake Brightsky API payloads, response objects, component factories
and a requests.get patch helper, so the api level tests
(test_weather_data.py) and the calculate() branch tests
(test_weather_data_branches.py) use identical building blocks.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Any

import pytest

from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.components.weather_data import weather_data as weather_module
from encodapy.components.weather_data.weather_data import WeatherData
from encodapy.config.types import AttributeTypes
from encodapy.utils.models import InputDataAttributeModel, StaticDataEntityModel
from encodapy.utils.units import DataUnits

CURRENT_WEATHER_PAYLOAD = {
    "weather": {
        "temperature": 21.5 + 273.15,
        "relative_humidity": 45.0,
        "pressure_msl": 1024.2 * 100,
        "dew_point": 9.7 + 273.15,
        "solar_60": 94440,
    }
}

FORECAST_WEATHER_PAYLOAD = {
    "weather": [
        {
            "timestamp": "2026-09-29T14:00:00+02:00",
            "temperature": 22.3 + 273.15,
            "solar": 250000,
        },
        {
            "timestamp": "2026-09-29T15:00:00+02:00",
            "temperature": 22.8 + 273.15,
            "solar": 460000,
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


class FakeResponse:  # pylint: disable=too-few-public-methods
    """Minimal stand-in for a requests.Response object.

    A payload of None simulates a response body that is no valid JSON
    (e.g. a html error page of a gateway), json() then raises a
    JSONDecodeError like requests would.
    """

    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None,
        body: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = body if body is not None else str(payload)

    def json(self) -> dict[str, Any]:
        """Return the payload of the fake api response."""
        if self._payload is None:
            raise JSONDecodeError("Expecting value", self.text, 0)
        return self._payload


def static_entities() -> list[StaticDataEntityModel]:
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


def component_config(outputs: dict[str, dict[str, str]]) -> ControllerComponentModel:
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


def make_component(
    outputs: dict[str, dict[str, str]] | None = None,
) -> WeatherData:
    """Create a fully initialized WeatherData component without API calls."""
    return WeatherData(
        config=component_config(outputs or ALL_OUTPUTS),
        component_id="weatherdata",
        static_data=static_entities(),
    )


def patch_requests_get(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, FakeResponse],
    error: Exception | None = None,
) -> list[dict[str, Any]]:
    """Replace requests.get of the weather module and record all calls."""
    calls: list[dict[str, Any]] = []

    def fake_get(
        url: str, params: dict | None = None, timeout: float | None = None
    ) -> FakeResponse:
        calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        if error is not None:
            raise error
        for suffix, response in responses.items():
            if url.endswith(suffix):
                return response
        return FakeResponse(404, {"message": f"unexpected url: {url}"})

    monkeypatch.setattr(weather_module.requests, "get", fake_get)
    return calls


def default_responses() -> dict[str, FakeResponse]:
    """Create the default fake responses for both brightsky api endpoints."""
    return {
        "/current_weather": FakeResponse(200, CURRENT_WEATHER_PAYLOAD),
        "/weather": FakeResponse(200, FORECAST_WEATHER_PAYLOAD),
    }


def elapsed_time() -> datetime:
    """Return a time in the past to force a refetch in calculate()."""
    return datetime.now(weather_module.WEATHER_DATA_TZ) - timedelta(minutes=1)


def output_dump(component: WeatherData) -> dict[str, Any]:
    """Return the dumped output data of the component."""
    return component.output_data.model_dump()
