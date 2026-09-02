"""Tests for MQTT data query functionality in EnCoDaPy."""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

from datetime import datetime, timezone

from encodapy.config import AttributeTypes, Interfaces, DataQueryTypes
from encodapy.config.env_values import MQTTEnvVariables
from encodapy.config.models import AttributeModel, InputModel
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.models import InputDataEntityModel


def test_get_data_from_mqtt_success():
    """Test get_data_from_mqtt with available data in message store."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")
    connection.mqtt_message_store = {
        "encodapy/TestInput:001/temperature": {
            "entity_id": "test_input",
            "attribute_id": "temperature",
            "value": 22.5,
            "unit": None,
            "timestamp": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        },
    }
    entity = InputModel(
        id="test_input",
        interface=Interfaces.MQTT,
        id_interface="TestInput:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE
            )
        ],
    )
    result = connection.get_data_from_mqtt(method=DataQueryTypes.CALCULATION, entity=entity)
    assert isinstance(result, InputDataEntityModel)
    assert result.id == "test_input"
    assert len(result.attributes) == 1
    attr = result.attributes[0]
    assert attr.data == 22.5
    assert attr.data_available is True


def test_get_data_from_mqtt_missing_topic():
    """Test get_data_from_mqtt with missing topics in message store."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")
    connection.mqtt_message_store = {}
    entity = InputModel(
        id="test_input",
        interface=Interfaces.MQTT,
        id_interface="TestInput:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE
            )
        ],
    )
    result = connection.get_data_from_mqtt(method=DataQueryTypes.CALCULATION, entity=entity)
    assert isinstance(result, InputDataEntityModel)
    assert result.id == "test_input"
    assert len(result.attributes) == 1
    attr = result.attributes[0]
    assert attr.data is None
    assert attr.data_available is False
