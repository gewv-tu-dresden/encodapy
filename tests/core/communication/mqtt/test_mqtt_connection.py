"""Tests for MQTT connection and configuration management in EnCoDaPy."""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import os
from unittest.mock import MagicMock, patch

import pytest
import paho.mqtt.client as mqtt

from encodapy.config import AttributeTypes, Interfaces
from encodapy.config.env_values import MQTTEnvVariables
from encodapy.config.models import AttributeModel, InputModel
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.error_handling import NotSupportedError


def test_load_mqtt_params_default():
    """Test loading MQTT parameters with default configuration."""
    connection = MqttConnection()
    with patch.dict(os.environ, {"MQTT_HOST": "localhost", "MQTT_PORT": "1883"}):
        connection.load_mqtt_params()
    assert connection.mqtt_params.host == "localhost"
    assert connection.mqtt_params.port == 1883


def test_mqtt_connection_init():
    """Test MqttConnection initialization."""
    connection = MqttConnection()
    # These are type hints, not actual attributes until set
    assert hasattr(connection, "mqtt_client")
    assert connection.mqtt_client is None


def test_assemble_topic_parts_basic():
    """Test assemble_topic_parts with basic parts."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["part1", "part2", "part3"])
    assert result == "part1/part2/part3"


def test_assemble_topic_parts_with_none_and_empty():
    """Test assemble_topic_parts handles None and empty strings."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["part1", None, "", "part2"])
    assert result == "part1/part2"


def test_assemble_topic_parts_empty_list():
    """Test assemble_topic_parts with empty list raises error."""
    connection = MqttConnection()
    with pytest.raises(ValueError):
        connection.assemble_topic_parts([])


def test_prepare_mqtt_message_store_success():
    """Test preparing MQTT message store with valid configuration."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")
    connection.config = MagicMock()
    connection.config.inputs = [
        InputModel(
            id="test_input",
            interface=Interfaces.MQTT,
            id_interface="TestInput:001",
            attributes=[
                AttributeModel(id="temp", id_interface="temperature", type=AttributeTypes.VALUE),
            ],
        )
    ]
    connection.prepare_mqtt_message_store()
    assert len(connection.mqtt_message_store) == 2
    assert "encodapy/TestInput:001" in connection.mqtt_message_store
    assert "encodapy/TestInput:001/temperature" in connection.mqtt_message_store


def test_subscribe_no_client():
    """Test subscribe method without MQTT client raises error."""
    connection = MqttConnection()
    connection.mqtt_client = None
    with pytest.raises(NotSupportedError):
        connection.subscribe("test/topic")


def test_stop_mqtt_client_success():
    """Test stop_mqtt_client stops the MQTT client loop."""
    connection = MqttConnection()
    mock_client = MagicMock(spec=mqtt.Client)
    connection.mqtt_client = mock_client
    connection._mqtt_loop_running = True
    connection.stop_mqtt_client()
    assert connection._mqtt_loop_running is False
    mock_client.loop_stop.assert_called_once()
    mock_client.disconnect.assert_called_once()
