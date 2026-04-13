import pytest

from encodapy.config.models import AttributeModel
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.units import DataUnits


def test_adjust_units_for_fiware_converts_value_and_metadata() -> None:
    connection = FiwareConnection()
    attribute = AttributeModel(id="power", value=1000.0, unit=DataUnits.WTT)

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.KWT,
    )

    assert adjusted_attribute.value == pytest.approx(1.0)
    assert adjusted_attribute.unit == DataUnits.KWT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.KWT.value
        for item in metadata
    )


def test_adjust_units_for_fiware_preserves_actual_unit_metadata_on_failure() -> None:
    connection = FiwareConnection()
    attribute = AttributeModel(id="power", value=1000.0, unit=DataUnits.WTT)

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.DEGREECELSIUS,
    )

    assert adjusted_attribute.value == 1000.0
    assert adjusted_attribute.unit == DataUnits.WTT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.WTT.value
        for item in metadata
    )
