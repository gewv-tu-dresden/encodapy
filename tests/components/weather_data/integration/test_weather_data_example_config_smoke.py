"""
Smoke test for the 10_brightsky_weather_service example configuration.

Test uses a fake brightsky API to avoid real network calls and to ensure stable test results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta
import pytz
import pytest

from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.components.weather_data import weather_data as weather_data_module
from encodapy.components.weather_data.weather_data import WeatherData
from encodapy.config.types import AttributeTypes
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import DataUnits

# The following payloads are used to simulate responses from the brightsky API.
CURRENT_WEATHER_PAYLOAD = {
    "weather": {
        "temperature": 21.5,
        "relative_humidity": 45.0,
        "pressure_msl": 1024.2,
        "dew_point": 9.7,
        "solar_60": 0.608,
    }
}

FORECAST_WEATHER_PAYLOAD = {
    "weather": [
        {
            "timestamp": "2026-09-29T14:00:00+02:00",
            "temperature": 22.3,
            "solar": 0.644,
        },
        {
            "timestamp": "2026-09-29T15:00:00+02:00",
            "temperature": 22.8,
            "solar": 0.625,
        },
        {
            "timestamp": "2026-09-29T16:00:00+02:00",
            "temperature": 22.7,
            "solar": 0.472,
        },
    ]
}


class _FakeResponse:  # pylint: disable=too-few-public-methods
    """Minimal stand-in for a requests.Response object."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        """Return the payload of the fake api response."""
        return self._payload


def _example_dir() -> Path:
    """Return the absolute path to the brightsky weather example directory."""
    return (
        Path(__file__).resolve().parents[4]
        / "examples"
        / "10_brightsky_weather_service"
    )


def _load_component_config(example_dir: Path) -> ControllerComponentModel:
    """Load the weatherdata component section from the example config file."""
    config_path = example_dir / "config.json"
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_component = raw_config["controller_components"][0]
    return ControllerComponentModel.model_validate(raw_component)


def _load_static_entities(example_dir: Path) -> list[StaticDataEntityModel]:
    """Load the static config values (coordinates and time intervals) of the example."""
    static_data_path = example_dir / "static_data.json"
    raw_static = json.loads(static_data_path.read_text(encoding="utf-8"))

    attributes = []
    for raw_attribute in raw_static["staticdata"][0]["attributes"]:
        value: float | str = raw_attribute["value"]
        if isinstance(value, str):
            value = float(value)
        attributes.append(
            {
                "id": raw_attribute["id"],
                "value": value,
                "unit": DataUnits(raw_attribute["unit"]),
            }
        )

    return [
        StaticDataEntityModel(
            id="weatherdata",
            attributes=[
                InputDataAttributeModel(
                    id=attribute["id"],
                    data=attribute["value"],
                    unit=attribute["unit"],
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=None,
                )
                for attribute in attributes
            ],
        )
    ]


def _fake_brightsky_api(api_calls: list[dict[str, Any]]):
    """Return a fake requests.get which serves canned brightsky responses."""

    def fake_get(url: str, params: dict | None = None, timeout: float | None = None):
        api_calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        if url.endswith("/current_weather"):
            return _FakeResponse(200, CURRENT_WEATHER_PAYLOAD)
        if url.endswith("/weather"):
            return _FakeResponse(200, FORECAST_WEATHER_PAYLOAD)
        return _FakeResponse(404, {"message": f"unexpected url: {url}"})

    return fake_get


@pytest.mark.integration
def test_example_config_smoke_runs_weather_data_component(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the real brightsky weather example configuration once on component level."""
    example_dir = _example_dir()
    static_entities = _load_static_entities(example_dir)

    api_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        weather_data_module.requests, "get", _fake_brightsky_api(api_calls)
    )

    component = WeatherData(
        config=_load_component_config(example_dir),
        component_id="weatherdata",
        static_data=static_entities,
    )

    input_model = InputDataModel(
        input_entities=[],
        output_entities=[],
        static_entities=static_entities,
    )

    component.set_input_data(input_model)
    component.calculate()

    # both api call methods (current and forecast) are configured in the example
    assert len(api_calls) == 2
    requested_urls = [call["url"] for call in api_calls]
    assert any(url.endswith("/current_weather") for url in requested_urls)
    assert any(url.endswith("/weather") for url in requested_urls)

    # the example static data (Dresden, 51.05 / 13.74) is used as api parameters
    for call in api_calls:
        assert call["params"]["lat"] == pytest.approx(51.05)
        assert call["params"]["lon"] == pytest.approx(13.74)
        # check date for forecast api call is within the last 15 minutes (to avoid stale data)
        if call["url"].endswith("/weather"):
            date = datetime.fromisoformat(call["params"]["date"])
            assert isinstance(date, datetime)
            now = datetime.now(pytz.timezone("Europe/Berlin"))
            assert now - timedelta(minutes=15) <= date <= now

    output = component.output_data.model_dump()
    assert output["temperature"]["value"] == pytest.approx(21.5)
    assert output["temperature"]["unit"] == DataUnits.DEGREECELSIUS
    assert output["relative_humidity"]["value"] == pytest.approx(45.0)
    assert output["pressure_msl"]["value"] == pytest.approx(1024.2)
    assert output["dew_point"]["value"] == pytest.approx(9.7)
    assert output["solar_60"]["value"] == pytest.approx(2188800.0)
    assert output["forecast_temperature"]["value"] == {
        "2026-09-29T14:00:00+02:00": 22.3,
        "2026-09-29T15:00:00+02:00": 22.8,
        "2026-09-29T16:00:00+02:00": 22.7,
    }
    assert output["forecast_solar"]["value"] == {
        "2026-09-29T14:00:00+02:00": 2318400.0,
        "2026-09-29T15:00:00+02:00": 2250000.0,
        "2026-09-29T16:00:00+02:00": 1699200.0,
    }

    # a second calculation within the configured time intervals
    # (1 minute current / 3 hours forecast) must reuse the data of the last api call
    component.calculate()
    assert len(api_calls) == 2
    second_output = component.output_data.model_dump()
    assert second_output["temperature"]["value"] == pytest.approx(21.5)
