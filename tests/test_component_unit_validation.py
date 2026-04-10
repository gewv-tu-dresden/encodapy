import pytest
from pydantic import Field

from encodapy.components.basic_component_config import InputData
from encodapy.components.two_point_controller.two_point_controller_config import (
    TwoPointControllerConfigData,
)
from encodapy.utils.datapoints import DataPointNumber, DataPointString
from encodapy.utils.units import DataUnits


class DemoInputData(InputData):
    temperature: DataPointNumber = Field(..., json_schema_extra={"unit": "KEL"})
    status_text: DataPointString = Field(..., json_schema_extra={"unit": "KWT"})


def test_component_data_converts_numeric_values_to_field_unit() -> None:
    model = DemoInputData(
        temperature=DataPointNumber(value=0.0, unit=DataUnits.DEGREECELSIUS),
        status_text=DataPointString(value="on", unit=DataUnits.WTT),
    )

    assert model.temperature.value == pytest.approx(273.15)
    assert model.temperature.unit == DataUnits.KELVIN


def test_component_data_does_not_relabel_non_convertible_values() -> None:
    model = DemoInputData(
        temperature=DataPointNumber(value=273.15, unit=DataUnits.KELVIN),
        status_text=DataPointString(value="on", unit=DataUnits.WTT),
    )

    assert model.status_text.value == "on"
    assert model.status_text.unit == DataUnits.WTT


def test_two_point_controller_harmonizes_hysteresis_unit_to_setpoint() -> None:
    model = TwoPointControllerConfigData(
        hysteresis=DataPointNumber(value=500.0, unit=DataUnits.WTT),
        setpoint=DataPointNumber(value=1.0, unit=DataUnits.KWT),
    )

    assert model.hysteresis.value == pytest.approx(0.5)
    assert model.hysteresis.unit == DataUnits.KWT
