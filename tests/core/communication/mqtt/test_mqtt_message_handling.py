"""Tests for MQTT message handling and callback functions in EnCoDaPy."""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from encodapy.config.env_values import MQTTEnvVariables
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.error_handling import NotSupportedError


def test_extract_payload_value_and_timestamp_json_with_value():
    """Test _extract_payload_value_and_timestamp with JSON containing value field."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(timestamp_key="TimeInstant")
    fallback_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    value, timestamp = connection._extract_payload_value_and_timestamp(
        '{"value": 42.5, "other": "data"}', fallback_timestamp
    )
    assert value == 42.5
    assert timestamp == fallback_timestamp


def test_extract_payload_value_and_timestamp_json_with_timestamp_key():
    """Test _extract_payload_value_and_timestamp with JSON containing timestamp key."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(timestamp_key="TimeInstant")
    fallback_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    value, timestamp = connection._extract_payload_value_and_timestamp(
        '{"value": 42.5, "TimeInstant": "2024-01-15T12:00:00+0000"}',
        fallback_timestamp
    )
    assert value == 42.5
    assert timestamp == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_extract_payload_value_and_timestamp_numeric_string():
    """Test _extract_payload_value_and_timestamp with numeric string payload."""
    connection = MqttConnection()
    fallback_timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    value, _ = connection._extract_payload_value_and_timestamp("22.5", fallback_timestamp)
    assert value == 22.5
    assert isinstance(value, float)


def test_sanitize_embedded_payload_value_none():
    """Test _sanitize_embedded_payload_value with None value."""
    value = MqttConnection._sanitize_embedded_payload_value(None, "__TEST__")
    assert value == ""


def test_sanitize_embedded_payload_value_complex_type():
    """Test _sanitize_embedded_payload_value with complex type."""
    assert MqttConnection._sanitize_embedded_payload_value({"key": "value"}, "__TEST__") == ""
    assert MqttConnection._sanitize_embedded_payload_value([1, 2, 3], "__TEST__") == ""


def test_sanitize_embedded_payload_value_string_with_special_chars():
    """Test _sanitize_embedded_payload_value with string containing special characters."""
    assert MqttConnection._sanitize_embedded_payload_value('test"value', "__TEST__") == ""
    assert MqttConnection._sanitize_embedded_payload_value('test\\value', "__TEST__") == ""


def test_sanitize_embedded_payload_value_valid_string():
    """Test _sanitize_embedded_payload_value with valid string."""
    assert (
        MqttConnection._sanitize_embedded_payload_value("valid_string", "__TEST__")
        == "valid_string"
    )


def test_sanitize_embedded_payload_value_number():
    """Test _sanitize_embedded_payload_value with numeric value."""
    assert MqttConnection._sanitize_embedded_payload_value(42.5, "__TEST__") == "42.5"
    assert MqttConnection._sanitize_embedded_payload_value(42, "__TEST__") == "42"


def test_sanitize_embedded_payload_value_boolean():
    """Test _sanitize_embedded_payload_value with boolean value."""
    assert MqttConnection._sanitize_embedded_payload_value(True, "__TEST__") == "True"
    assert MqttConnection._sanitize_embedded_payload_value(False, "__TEST__") == "False"


def test_subscribe_no_client():
    """Test subscribe method without MQTT client raises error."""
    connection = MqttConnection()
    connection.mqtt_client = None
    with pytest.raises(NotSupportedError):
        connection.subscribe("test/topic")


def test_subscribe_to_message_store_topics_empty_store():
    """Test subscribe_to_message_store_topics with empty message store raises error."""
    connection = MqttConnection()
    connection.mqtt_client = MagicMock()
    connection.mqtt_message_store = {}
    with pytest.raises(NotSupportedError):
        connection.subscribe_to_message_store_topics()
