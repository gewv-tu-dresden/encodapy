"""Tests for output handling and datatype logging in the basic service."""

# pylint: disable=protected-access

import asyncio

from filip.models.base import DataType

from encodapy.config import AttributeModel, Interfaces, OutputModel
from encodapy.service.basic_service import ControllerBasicService
from encodapy.utils.models import (
    DataTransferComponentModel,
    OutputDataEntityModel,
    OutputDataModel,
)


def _build_service(outputs: list[OutputModel]) -> ControllerBasicService:
    """Create a service instance without __init__ side effects."""
    service = object.__new__(ControllerBasicService)
    service.config = type("ConfigStub", (), {"outputs": outputs})()
    return service


def _build_output_entity(interface: Interfaces) -> OutputModel:
    """Create a minimal output configuration for one interface."""
    return OutputModel(
        id="out_1",
        interface=interface,
        attributes=[
            AttributeModel(
                id="attr_1",
                datatype=DataType.NUMBER,
            )
        ],
        commands=[],
    )


def _build_output_data(value):
    """Create a minimal OutputDataModel containing one attribute value."""
    return OutputDataModel(
        entities=[
            OutputDataEntityModel(
                id="out_1",
                attributes=[
                    AttributeModel(
                        id="attr_1",
                        value=value,
                        datatype=DataType.NUMBER,
                    )
                ],
                commands=[],
            )
        ]
    )


def test_send_outputs_fiware_is_called_once():
    """Ensure FIWARE output is sent only once per entity."""
    output_entity = _build_output_entity(Interfaces.FIWARE)
    service = _build_service([output_entity])

    calls = []

    async def fake_send_data_to_fiware(**kwargs):
        """Capture calls of the FIWARE send path for assertions."""
        calls.append(kwargs)

    service._send_data_to_fiware = fake_send_data_to_fiware
    data_output = _build_output_data(value=1.23)

    asyncio.run(service.send_outputs(data_output=data_output))

    assert len(calls) == 1


def test_send_outputs_file_is_called_once():
    """Ensure FILE output is written only once per entity."""
    output_entity = _build_output_entity(Interfaces.FILE)
    service = _build_service([output_entity])

    calls = []

    def fake_send_data_to_json_file(**kwargs):
        """Capture calls of the FILE send path for assertions."""
        calls.append(kwargs)

    service.send_data_to_json_file = fake_send_data_to_json_file
    data_output = _build_output_data(value=7)

    asyncio.run(service.send_outputs(data_output=data_output))

    assert len(calls) == 1


def test_validate_datatype_against_value_logs_mismatch_without_overriding(monkeypatch):
    """Log type mismatches without changing the configured datatype."""
    output_entity = _build_output_entity(Interfaces.FILE)
    service = _build_service([output_entity])

    messages = []

    def fake_warning(message):
        """Capture warning messages for later assertions."""
        messages.append(message)

    import encodapy.service.basic_service as basic_service_module

    monkeypatch.setattr(basic_service_module.logger, "warning", fake_warning)

    configured_attribute = AttributeModel(id="attr_1", datatype=DataType.NUMBER)
    component = DataTransferComponentModel(
        entity_id="out_1",
        attribute_id="attr_1",
        value=True,
    )

    returned_datatype = service._validate_datatype_against_value(
        configured_attribute,
        component,
    )

    assert returned_datatype == DataType.NUMBER
    assert len(messages) == 1
    assert "Datatype mismatch for attribute attr_1" in messages[0]


def test_is_geojson_detects_feature_collection():
    """Recognize a FeatureCollection as valid GeoJSON."""
    output_entity = _build_output_entity(Interfaces.FILE)
    service = _build_service([output_entity])

    geojson_value = {
        "type": "FeatureCollection",
        "features": [],
    }

    assert service._is_geojson(geojson_value) is True


def test_is_geojson_rejects_plain_dict():
    """Reject a plain dict without GeoJSON structure."""
    output_entity = _build_output_entity(Interfaces.FILE)
    service = _build_service([output_entity])

    plain_value = {
        "foo": "bar",
        "value": 1,
    }

    assert service._is_geojson(plain_value) is False
