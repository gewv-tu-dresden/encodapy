"""Tests for MQTT data sending functionality in EnCoDaPy."""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

from unittest.mock import MagicMock

import pytest

from encodapy.config import Interfaces, MQTTFormatTypes
from encodapy.config.env_values import MQTTEnvVariables
from encodapy.config.models import AttributeModel, OutputModel
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.error_handling import ConfigError, NotSupportedError


def test_prepare_mqtt_topic_plain_format():
    """Test _prepare_mqtt_topic with PLAIN MQTT format."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")
    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.PLAIN,
        output_entity__id_interface="TestOutput:001",
        output_attribute__id_interface="temperature",
    )
    assert topic == "encodapy/TestOutput:001/temperature"


def test_prepare_mqtt_topic_fiware_attr_format():
    """Test _prepare_mqtt_topic with FIWARE_ATTR MQTT format."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")
    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
        output_entity__id_interface="TestOutput:001",
        output_attribute__id_interface="temperature",
    )
    assert topic == "encodapy/TestOutput:001/attrs"


def test_prepare_mqtt_payload_plain_format():
    """Test _prepare_mqtt_payload with PLAIN MQTT format."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[]
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=22.5,
        mqtt_format=MQTTFormatTypes.PLAIN
    )
    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity, output_attribute=output_attribute
    )
    assert payload == 22.5


def test_prepare_mqtt_payload_fiware_attr_format():
    """Test _prepare_mqtt_payload with FIWARE_ATTR MQTT format."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[]
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=22.5,
        mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
    )
    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity, output_attribute=output_attribute
    )
    assert isinstance(payload, dict)
    assert payload["temperature"] == 22.5


def test_send_data_to_mqtt_not_connected():
    """Test send_data_to_mqtt when client is not connected."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables()
    connection._mqtt_connected = False
    connection.mqtt_client = MagicMock()
    connection.config = MagicMock()
    connection.publish = MagicMock()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[]
    )
    output_attributes = [
        AttributeModel(
            id="temp",
            id_interface="temperature",
            value=22.5,
            mqtt_format=MQTTFormatTypes.PLAIN
        )
    ]
    connection.send_data_to_mqtt(output_entity=output_entity, output_attributes=output_attributes)
    connection.publish.assert_not_called()


def test_send_data_to_mqtt_no_client():
    """Test send_data_to_mqtt without MQTT client raises error."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables()
    connection.mqtt_client = None
    connection._mqtt_connected = True
    connection.config = MagicMock()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[]
    )
    output_attributes = [
        AttributeModel(
            id="temp",
            id_interface="temperature",
            value=22.5,
            mqtt_format=MQTTFormatTypes.PLAIN
        )
    ]
    with pytest.raises(NotSupportedError):
        connection.send_data_to_mqtt(
            output_entity=output_entity, output_attributes=output_attributes
        )


def test_send_data_to_mqtt_no_config():
    """Test send_data_to_mqtt without config raises error."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables()
    connection.mqtt_client = MagicMock()
    connection._mqtt_connected = True
    connection.config = None
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[]
    )
    output_attributes = [
        AttributeModel(
            id="temp",
            id_interface="temperature",
            value=22.5,
            mqtt_format=MQTTFormatTypes.PLAIN
        )
    ]
    with pytest.raises(ConfigError):
        connection.send_data_to_mqtt(
            output_entity=output_entity, output_attributes=output_attributes
        )


def test_publish_no_client():
    """Test publish method without MQTT client raises error."""
    connection = MqttConnection()
    connection.mqtt_client = None
    with pytest.raises(NotSupportedError):
        connection.publish(topic="test/topic", payload="test_payload")


def test_prepare_payload_for_publish_dict():
    """Test prepare_payload_for_publish with dict payload."""
    connection = MqttConnection()
    result = connection.prepare_payload_for_publish({"value": 42, "unit": "CEL"})
    assert isinstance(result, str)
    assert result == '{"value": 42, "unit": "CEL"}'


def test_prepare_payload_for_publish_number():
    """Test prepare_payload_for_publish with numeric payload."""
    connection = MqttConnection()
    assert connection.prepare_payload_for_publish(42.5) == "42.5"
    assert connection.prepare_payload_for_publish(42) == "42"


def test_prepare_payload_for_publish_bool():
    """Test prepare_payload_for_publish with boolean payload."""
    connection = MqttConnection()
    assert connection.prepare_payload_for_publish(True) == "True"
    assert connection.prepare_payload_for_publish(False) == "False"


def test_prepare_payload_for_publish_none():
    """Test prepare_payload_for_publish with None payload."""
    connection = MqttConnection()
    assert connection.prepare_payload_for_publish(None) is None
