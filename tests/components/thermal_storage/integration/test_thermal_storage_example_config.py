"""Integration test for the thermal storage component.

The test uses the component configuration of the 06_thermal_storage_service
example (connection limits calculation method, five storage sensors and the
load connection sensors) and runs a full calculation cycle on component level.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.components.thermal_storage.thermal_storage import ThermalStorage
from encodapy.config.types import AttributeTypes
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    InputDataModel,
    OutputDataEntityModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import DataUnits

STORAGE_TIME = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

STORAGE_TEMPERATURES = [85.0, 75.0, 65.0, 55.0, 45.0]
LOAD_TEMPERATURE_IN = 45.0
LOAD_TEMPERATURE_OUT = 55.0


def _example_dir() -> Path:
    """Return the absolute path to the thermal storage example directory."""
    return (
        Path(__file__).resolve().parents[4] / "examples" / "06_thermal_storage_service"
    )


def _load_component_config(example_dir: Path) -> ControllerComponentModel:
    """Load the thermal storage component section from the example config file.

    The calibration database path is disabled, so that the test does not
    write the default calibration database into the working directory.
    """
    config_path = example_dir / "config.json"
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_component = raw_config["controller_components"][0]
    raw_component["config"]["calibration"] = {"value": {"db_path": None}}
    return ControllerComponentModel.model_validate(raw_component)


def _static_entities() -> list[StaticDataEntityModel]:
    """Create the static data entities with the storage parameters."""
    sensor_config = {
        "storage_sensors": [
            {
                "height": height,
                "limits": {
                    "minimal_temperature": 40.0,
                    "maximal_temperature": 90.0,
                    "reference_temperature": 40.0,
                },
            }
            for height in [10.0, 30.0, 50.0, 70.0, 90.0]
        ]
    }

    def _attribute(
        attribute_id: str, value: Any, unit: DataUnits | None = None
    ) -> InputDataAttributeModel:
        return InputDataAttributeModel.model_validate(
            {
                "id": attribute_id,
                "data": value,
                "unit": unit,
                "data_type": AttributeTypes.VALUE.value,
                "data_available": True,
                "latest_timestamp_input": None,
            }
        )

    return [
        StaticDataEntityModel(
            id="thermal_storage",
            attributes=[
                _attribute("volume", 5.0, DataUnits.MTQ),
                _attribute("medium", "water"),
                _attribute("sensor_config", sensor_config),
            ],
        )
    ]


def _input_data() -> InputDataModel:
    """Create the input data with all storage and load connection sensors."""
    attributes = [
        InputDataAttributeModel(
            id=f"temperature_{index}",
            data=temperature,
            unit=DataUnits.DEGREECELSIUS,
            data_type=AttributeTypes.VALUE,
            data_available=True,
            latest_timestamp_input=STORAGE_TIME,
        )
        for index, temperature in enumerate(STORAGE_TEMPERATURES, start=1)
    ]
    attributes.append(
        InputDataAttributeModel(
            id="temperature_in",
            data=LOAD_TEMPERATURE_IN,
            unit=DataUnits.DEGREECELSIUS,
            data_type=AttributeTypes.VALUE,
            data_available=True,
            latest_timestamp_input=STORAGE_TIME,
        )
    )
    attributes.append(
        InputDataAttributeModel(
            id="temperature_out",
            data=LOAD_TEMPERATURE_OUT,
            unit=DataUnits.DEGREECELSIUS,
            data_type=AttributeTypes.VALUE,
            data_available=True,
            latest_timestamp_input=STORAGE_TIME,
        )
    )
    return InputDataModel(
        input_entities=[
            InputDataEntityModel(id="thermal_storage", attributes=attributes)
        ],
        output_entities=[OutputDataEntityModel(id="thermal_storage")],
        static_entities=[],
    )


@pytest.mark.integration
def test_example_config_full_calculation_cycle() -> None:
    """Run the example configuration through a full component calculation."""
    component = ThermalStorage(
        config=_load_component_config(_example_dir()),
        component_id="thermal_storage",
        static_data=_static_entities(),
    )

    assert component.sensor_volumes is not None
    assert len(component.sensor_volumes) == 5

    component.set_input_data(_input_data())
    component.calculate()

    output = component.output_data

    assert output.storage__level is not None
    assert output.storage__energy is not None
    assert output.storage__energy_nominal is not None
    assert output.storage__loading_potential_nominal is not None

    level = output.storage__level.value
    nominal_energy = output.storage__energy_nominal.value
    current_energy = output.storage__energy.value

    assert output.storage__level.unit is DataUnits.PERCENT
    assert output.storage__energy.unit is DataUnits.WHR
    assert output.storage__energy_nominal.unit is DataUnits.WHR
    assert output.storage__loading_potential_nominal.unit is DataUnits.WHR

    assert 0.0 <= level <= 100.0
    assert nominal_energy > 0.0
    assert 0.0 < current_energy < nominal_energy

    # the current energy is derived from the state of charge
    assert current_energy == pytest.approx(level / 100 * nominal_energy, rel=0.01)

    # the loading potential closes the gap to the nominal energy
    assert output.storage__loading_potential_nominal.value == pytest.approx(
        nominal_energy - current_energy, abs=0.02
    )

    # the temperature history is stored for the load level check
    assert set(component.sensor_values_stored) == {0, 1, 2, 3, 4}


@pytest.mark.integration
def test_example_config_level_is_stable_over_two_cycles() -> None:
    """A second calculation with unchanged inputs returns the same level."""
    component = ThermalStorage(
        config=_load_component_config(_example_dir()),
        component_id="thermal_storage",
        static_data=_static_entities(),
    )
    component.set_input_data(_input_data())

    component.calculate()
    first_level = component.output_data.storage__level
    assert first_level is not None

    component.set_input_data(
        _input_data_with_later_time(
            STORAGE_TIME.replace(minute=30),
        )
    )
    component.calculate()
    second_level = component.output_data.storage__level
    assert second_level is not None

    assert second_level.value == pytest.approx(first_level.value, abs=0.5)


def _input_data_with_later_time(time: datetime) -> InputDataModel:
    """Create the input data with a different measurement time."""
    data = _input_data()
    for entity in data.input_entities:
        for attribute in entity.attributes:
            attribute.latest_timestamp_input = time
    return data
