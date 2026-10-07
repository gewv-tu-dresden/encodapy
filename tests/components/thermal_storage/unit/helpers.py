"""Shared test helpers for the ThermalStorage component unit tests.

Provides component factories and input data builders, so the calculation
tests and the branch tests use identical building blocks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.components.thermal_storage.thermal_storage import ThermalStorage
from encodapy.components.thermal_storage.thermal_storage_config import (
    ThermalStorageCalculationMethods,
)
from encodapy.config.types import AttributeTypes
from encodapy.utils.mediums import Medium, get_medium_parameter
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    InputDataModel,
    OutputDataEntityModel,
)
from encodapy.utils.units import DataUnits

STORAGE_ID = "thermal_storage"
VOLUME = 10.0
STORAGE_TIME = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

SENSOR_LIMITS = {
    "minimal_temperature": 40.0,
    "maximal_temperature": 90.0,
    "reference_temperature": 40.0,
}


def sensor_config(heights: list[float]) -> dict[str, Any]:
    """Create a sensor configuration with identical limits for all sensors."""
    return {
        "storage_sensors": [
            {"height": height, "limits": dict(SENSOR_LIMITS)} for height in heights
        ]
    }


def component_config(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    calculation_method: str = ThermalStorageCalculationMethods.STATIC_LIMITS.value,
    heights: list[float] | None = None,
    number_of_sensors: int = 3,
    with_load_connection_sensors: bool = False,
    load_level_check: dict[str, Any] | None = None,
    volume: float = VOLUME,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a valid thermal storage component configuration as dict."""
    inputs = {
        f"temperature_{index}": {
            "entity": STORAGE_ID,
            "attribute": f"temperature_{index}",
        }
        for index in range(1, number_of_sensors + 1)
    }
    if with_load_connection_sensors:
        inputs["load_temperature_in"] = {
            "entity": STORAGE_ID,
            "attribute": "temperature_in",
        }
        inputs["load_temperature_out"] = {
            "entity": STORAGE_ID,
            "attribute": "temperature_out",
        }

    config: dict[str, Any] = {
        "id": STORAGE_ID,
        "type": "thermal_storage",
        "inputs": inputs,
        "outputs": {
            "storage__level": {
                "entity": STORAGE_ID,
                "attribute": "storage__level",
            }
        },
        "config": {
            "volume": {"value": volume},
            "medium": {"value": "water"},
            "sensor_config": {"value": sensor_config(heights or [10.0, 50.0, 90.0])},
            "calculation_method": {"value": calculation_method},
            "calibration": {"value": {"db_path": None}},
        },
    }
    if load_level_check is not None:
        config["config"]["load_level_check"] = {"value": load_level_check}
    if config_overrides is not None:
        config["config"].update(config_overrides)
    return config


def input_data(
    temperatures: list[float],
    load_temperature_in: float | None = None,
    load_temperature_out: float | None = None,
    time: datetime | None = STORAGE_TIME,
) -> InputDataModel:
    """Create an input data model with storage sensor temperatures in °C."""
    attributes: list[InputDataAttributeModel] = []

    def _attribute(attribute_id: str, value: float) -> InputDataAttributeModel:
        return InputDataAttributeModel(
            id=attribute_id,
            data=value,
            unit=DataUnits.DEGREECELSIUS,
            data_type=AttributeTypes.VALUE,
            data_available=True,
            latest_timestamp_input=time,
        )

    for index, temperature in enumerate(temperatures, start=1):
        attributes.append(_attribute(f"temperature_{index}", temperature))
    if load_temperature_in is not None:
        attributes.append(_attribute("temperature_in", load_temperature_in))
    if load_temperature_out is not None:
        attributes.append(_attribute("temperature_out", load_temperature_out))

    return InputDataModel(
        input_entities=[InputDataEntityModel(id=STORAGE_ID, attributes=attributes)],
        output_entities=[OutputDataEntityModel(id=STORAGE_ID)],
        static_entities=[],
    )


def make_component(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    temperatures: list[float],
    calculation_method: str = ThermalStorageCalculationMethods.STATIC_LIMITS.value,
    heights: list[float] | None = None,
    load_temperatures: tuple[float, float] | None = None,
    load_level_check: dict[str, Any] | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> ThermalStorage:
    """Create a fully initialized ThermalStorage component with input data.

    The component is prepared during initialization (BasicComponent.__init__
    calls prepare_component()), so the sensor volumes are already calculated.
    """
    config = component_config(
        calculation_method=calculation_method,
        heights=heights,
        number_of_sensors=len(temperatures),
        with_load_connection_sensors=load_temperatures is not None,
        load_level_check=load_level_check,
        config_overrides=config_overrides,
    )
    component = ThermalStorage(
        config=ControllerComponentModel.model_validate(config),
        component_id=STORAGE_ID,
    )
    load_in, load_out = (
        load_temperatures if load_temperatures is not None else (None, None)
    )
    component.set_input_data(input_data(temperatures, load_in, load_out))
    return component


def expected_energy(
    temperature_differences: list[float],
    volumes: list[float],
    temperatures: list[float],
) -> float:
    """Calculate the expected energy content in Wh using the medium parameters."""
    energy = 0.0
    for difference, volume, temperature in zip(
        temperature_differences, volumes, temperatures, strict=True
    ):
        medium = get_medium_parameter(medium=Medium.WATER, temperature=temperature)
        energy += difference * volume * medium.rho * medium.cp / 3.6
    return round(energy, 2)


def nominal_volumes(heights: list[float], volume: float = VOLUME) -> list[float]:
    """Calculate the expected volume per sensor for the given heights."""
    volumes = []
    height_ref = 0.0
    for index, height in enumerate(heights):
        if index == len(heights) - 1:
            height_new = 100.0
        else:
            height_new = (height + heights[index + 1]) / 2
        volumes.append((height_new - height_ref) / 100 * volume)
        height_ref = height_new
    return volumes
