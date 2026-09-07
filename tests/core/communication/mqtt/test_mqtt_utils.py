"""Utility function unit tests for MQTT connection in EnCoDaPy.

This module provides tests for utility functions in MqttConnection, focusing on:
- Connection preparation and TLS configuration
- Message store management
- Payload extraction and processing
- Topic assembly and preparation
- Data publishing and querying

Test Strategy:
- Unit tests with mocked dependencies (paho.mqtt.client, environment variables)
- Focus on utility methods and helper functions in MqttConnection class
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
import pytest
from pandas import DataFrame, Series

from encodapy.config import Interfaces, MQTTFormatTypes
from encodapy.config.env_values import MQTTEnvVariables
from encodapy.config.models import (
    AttributeModel,
    InputModel,
    OutputModel,
)
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.error_handling import ConfigError, NotSupportedError
from encodapy.config import AttributeTypes


# =============================================================================
# Fixtures for Advanced MQTT Tests
# =============================================================================

@pytest.fixture
def mock_mqtt_connection():
    """Create a mock MqttConnection instance with basic setup."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(
        host="test.broker",
        port=1883,
        topic_prefix="encodapy",
        username="testuser",
        password="testpass",
        tls_enabled=False,
    )
    connection.mqtt_client = MagicMock()
    connection.config = MagicMock()
    connection._mqtt_connected = False
    connection.mqtt_message_store = {}
    return connection


@pytest.fixture
def mock_mqtt_connection_connected():
    """Create a mock MqttConnection instance that is connected."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(
        host="test.broker",
        port=1883,
        topic_prefix="encodapy",
    )
    connection.mqtt_client = MagicMock()
    connection.config = MagicMock()
    connection._mqtt_connected = True
    connection.mqtt_message_store = {}
    return connection


@pytest.fixture
def mock_output_entity():
    """Create a mock OutputModel entity."""
    return OutputModel(
        id="test_output",
        interface=Interfaces.MQTT,
        id_interface="TestOutput:001",
        attributes=[],
    )


@pytest.fixture
def mock_input_entity():
    """Create a mock InputModel entity."""
    return InputModel(
        id="test_input",
        interface=Interfaces.MQTT,
        id_interface="TestInput:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
            ),
        ],
    )


@pytest.fixture
def mock_mqtt_client():
    """Create a mock paho MQTT client."""
    client = MagicMock()
    client.username_pw_set = MagicMock()
    client.tls_set = MagicMock()
    client.tls_insecure_set = MagicMock()
    client.connect = MagicMock()
    client.loop_start = MagicMock()
    client.loop_stop = MagicMock()
    client.disconnect = MagicMock()
    client.publish = MagicMock()
    client.subscribe = MagicMock()
    client.reconnect_delay_set = MagicMock()
    return client


# =============================================================================
# Tests for _sanitize_embedded_payload_value
# =============================================================================


def test_sanitize_embedded_payload_value_none():
    """Test _sanitize_embedded_payload_value with None value."""
    result = MqttConnection._sanitize_embedded_payload_value(None, "__TEST__")
    assert result == ""


def test_sanitize_embedded_payload_value_dict():
    """Test _sanitize_embedded_payload_value with dict value."""
    test_dict = {"key": "value"}
    result = MqttConnection._sanitize_embedded_payload_value(test_dict, "__TEST__")
    assert result == ""


def test_sanitize_embedded_payload_value_list():
    """Test _sanitize_embedded_payload_value with list value."""
    test_list = [1, 2, 3]
    result = MqttConnection._sanitize_embedded_payload_value(test_list, "__TEST__")
    assert result == ""


def test_sanitize_embedded_payload_value_string_valid():
    """Test _sanitize_embedded_payload_value with valid string."""
    result = MqttConnection._sanitize_embedded_payload_value("valid_string", "__TEST__")
    assert result == "valid_string"


def test_sanitize_embedded_payload_value_string_with_quotes():
    """Test _sanitize_embedded_payload_value with string containing quotes."""
    result = MqttConnection._sanitize_embedded_payload_value('test"value', "__TEST__")
    assert result == ""


def test_sanitize_embedded_payload_value_number():
    """Test _sanitize_embedded_payload_value with numeric value."""
    assert MqttConnection._sanitize_embedded_payload_value(42.5, "__TEST__") == "42.5"
    assert MqttConnection._sanitize_embedded_payload_value(42, "__TEST__") == "42"


def test_sanitize_embedded_payload_value_boolean():
    """Test _sanitize_embedded_payload_value with boolean value."""
    assert MqttConnection._sanitize_embedded_payload_value(True, "__TEST__") == "True"
    assert MqttConnection._sanitize_embedded_payload_value(False, "__TEST__") == "False"


# =============================================================================
# Tests for assemble_topic_parts
# =============================================================================


def test_assemble_topic_parts_basic():
    """Test assemble_topic_parts with basic parts."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["encodapy", "entity", "attr"])
    assert result == "encodapy/entity/attr"


def test_assemble_topic_parts_with_none():
    """Test assemble_topic_parts with None values."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["encodapy", None, "attr", ""])
    assert result == "encodapy/attr"


def test_assemble_topic_parts_with_trailing_slashes():
    """Test assemble_topic_parts with trailing slashes."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["encodapy/", "entity/", "attr"])
    assert result == "encodapy/entity/attr"


def test_assemble_topic_parts_empty_list():
    """Test assemble_topic_parts with empty list raises ValueError."""
    connection = MqttConnection()
    with pytest.raises(ValueError, match="list of parts cannot be empty"):
        connection.assemble_topic_parts([])


def test_assemble_topic_parts_single_part():
    """Test assemble_topic_parts with single part."""
    connection = MqttConnection()
    result = connection.assemble_topic_parts(["single"])
    assert result == "single"


# =============================================================================
# Tests for prepare_mqtt_message_store
# =============================================================================


def test_prepare_mqtt_message_store_no_config(mock_mqtt_connection):
    """Test prepare_mqtt_message_store without config raises ConfigError."""
    mock_mqtt_connection.config = None
    with pytest.raises(ConfigError, match="ConfigModel is not set"):
        mock_mqtt_connection.prepare_mqtt_message_store()


def test_prepare_mqtt_message_store_empty_input(mock_mqtt_connection):
    """Test prepare_mqtt_message_store with empty input list."""
    mock_mqtt_connection.config.inputs = []
    mock_mqtt_connection.prepare_mqtt_message_store()
    assert mock_mqtt_connection.mqtt_message_store == {}


def test_prepare_mqtt_message_store_non_mqtt_entity(mock_mqtt_connection):
    """Test prepare_mqtt_message_store ignores non-MQTT entities."""
    mock_mqtt_connection.config.inputs = [
        InputModel(
            id="test1",
            interface=Interfaces.FILE,
            id_interface="Test:001",
            attributes=[],
        ),
    ]
    mock_mqtt_connection.prepare_mqtt_message_store()
    assert mock_mqtt_connection.mqtt_message_store == {}


def test_prepare_mqtt_message_store_with_entity_and_attributes(mock_mqtt_connection):
    """Test prepare_mqtt_message_store with entity and attributes."""
    mock_mqtt_connection.config.inputs = [
        InputModel(
            id="test1",
            interface=Interfaces.MQTT,
            id_interface="Test:001",
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temperature",
                    type=AttributeTypes.VALUE,
                    value=22.5,
                ),
                AttributeModel(
                    id="hum",
                    id_interface="humidity",
                    type=AttributeTypes.VALUE,
                    value=65.0,
                ),
            ],
        ),
    ]
    mock_mqtt_connection.prepare_mqtt_message_store()

    # Check entity topic
    assert "encodapy/Test:001" in mock_mqtt_connection.mqtt_message_store
    entity_item = mock_mqtt_connection.mqtt_message_store["encodapy/Test:001"]
    assert entity_item["entity_id"] == "test1"
    assert entity_item["attribute_id"] is None
    assert entity_item["value"] is None

    # Check attribute topics
    assert "encodapy/Test:001/temperature" in mock_mqtt_connection.mqtt_message_store
    assert "encodapy/Test:001/humidity" in mock_mqtt_connection.mqtt_message_store

    temp_item = mock_mqtt_connection.mqtt_message_store["encodapy/Test:001/temperature"]
    assert temp_item["entity_id"] == "test1"
    assert temp_item["attribute_id"] == "temp"
    assert temp_item["value"] == 22.5


# =============================================================================
# Tests for _add_item_to_mqtt_message_store
# =============================================================================


def test_add_item_to_mqtt_message_store_new_topic(mock_mqtt_connection):
    """Test _add_item_to_mqtt_message_store with new topic."""
    mock_mqtt_connection._add_item_to_mqtt_message_store(
        topic="test/topic",
        entity_id="entity1",
        attribute_id="attr1",
        value=42.0,
        unit="CEL",
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )

    assert "test/topic" in mock_mqtt_connection.mqtt_message_store
    item = mock_mqtt_connection.mqtt_message_store["test/topic"]
    assert item["entity_id"] == "entity1"
    assert item["attribute_id"] == "attr1"
    assert item["value"] == 42.0
    assert item["unit"] == "CEL"
    assert item["timestamp"] == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_add_item_to_mqtt_message_store_overwrite_warning(mock_mqtt_connection):
    """Test _add_item_to_mqtt_message_store handles overwrite correctly."""
    # Add first item
    mock_mqtt_connection._add_item_to_mqtt_message_store(
        topic="test/topic",
        entity_id="entity1",
        attribute_id="attr1",
        value=42.0,
    )

    # Overwrite with second item - should work without error
    mock_mqtt_connection._add_item_to_mqtt_message_store(
        topic="test/topic",
        entity_id="entity2",
        attribute_id="attr2",
        value=43.0,
    )

    # Verify the store was updated with the new values
    store_item = mock_mqtt_connection.mqtt_message_store["test/topic"]
    assert store_item["entity_id"] == "entity2"
    assert store_item["attribute_id"] == "attr2"
    assert store_item["value"] == 43.0


# =============================================================================
# Tests for _extract_payload_value_and_timestamp
# =============================================================================


def test_extract_payload_value_and_timestamp_none_payload():
    """Test _extract_payload_value_and_timestamp with None payload."""
    connection = MqttConnection()
    connection._last_message_received = datetime(
        2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
    )

    value, timestamp = connection._extract_payload_value_and_timestamp(None)
    assert value is None
    assert timestamp == connection._last_message_received


def test_extract_payload_value_and_timestamp_empty_string():
    """Test _extract_payload_value_and_timestamp with empty string."""
    connection = MqttConnection()
    connection._last_message_received = datetime(
        2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
    )

    value, timestamp = connection._extract_payload_value_and_timestamp("")
    assert value is None
    assert timestamp == connection._last_message_received


def test_extract_payload_value_and_timestamp_non_string():
    """Test _extract_payload_value_and_timestamp with non-string payload."""
    connection = MqttConnection()
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    value, timestamp = connection._extract_payload_value_and_timestamp(
        42.5, fallback_ts
    )
    assert value == 42.5
    assert timestamp == fallback_ts


def test_extract_payload_value_and_timestamp_datetime_string():
    """Test _extract_payload_value_and_timestamp with datetime string."""
    connection = MqttConnection()
    connection._last_message_received = datetime(
        2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
    )
    datetime_str = "2024-01-15T10:30:00+00:00"

    value, timestamp = connection._extract_payload_value_and_timestamp(datetime_str)
    assert value == datetime_str
    # Datetime strings are returned as-is, with fallback timestamp
    assert timestamp == connection._last_message_received


def test_extract_payload_value_and_timestamp_json_with_value():
    """Test _extract_payload_value_and_timestamp with JSON containing value."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(timestamp_key="TimeInstant")
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    payload = '{"value": 42.5, "other": "data"}'
    value, timestamp = connection._extract_payload_value_and_timestamp(
        payload, fallback_ts
    )
    assert value == 42.5
    assert timestamp == fallback_ts


def test_extract_payload_value_and_timestamp_json_with_timestamp_key():
    """Test _extract_payload_value_and_timestamp with custom timestamp key."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(timestamp_key="TimeInstant")
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    payload = '{"value": 42.5, "TimeInstant": "2024-01-15T12:00:00+00:00"}'
    value, timestamp = connection._extract_payload_value_and_timestamp(
        payload, fallback_ts
    )
    assert value == 42.5
    assert timestamp == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_extract_payload_value_and_timestamp_numeric_string():
    """Test _extract_payload_value_and_timestamp with numeric string."""
    connection = MqttConnection()
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    value, _ = connection._extract_payload_value_and_timestamp("22.5", fallback_ts)
    assert value == 22.5


def test_extract_payload_value_and_timestamp_number_with_unit():
    """Test _extract_payload_value_and_timestamp extracts number from string with unit."""
    connection = MqttConnection()
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    value, _ = connection._extract_payload_value_and_timestamp("22.5 °C", fallback_ts)
    assert value == 22.5


def test_extract_payload_value_and_timestamp_invalid_json():
    """Test _extract_payload_value_and_timestamp with invalid JSON."""
    connection = MqttConnection()
    fallback_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    value, timestamp = connection._extract_payload_value_and_timestamp(
        "not valid json", fallback_ts
    )
    assert value == "not valid json"
    assert timestamp == fallback_ts


# =============================================================================
# Tests for prepare_payload_for_publish
# =============================================================================


def test_prepare_payload_for_publish_dict():
    """Test prepare_payload_for_publish with dict payload."""
    connection = MqttConnection()
    result = connection.prepare_payload_for_publish({"value": 42, "unit": "CEL"})
    assert isinstance(result, str)
    assert result == '{"value": 42, "unit": "CEL"}'


def test_prepare_payload_for_publish_list():
    """Test prepare_payload_for_publish with list payload."""
    connection = MqttConnection()
    result = connection.prepare_payload_for_publish([1, 2, 3])
    assert isinstance(result, str)
    assert result == "[1, 2, 3]"


def test_prepare_payload_for_publish_dataframe():
    """Test prepare_payload_for_publish with DataFrame payload."""
    connection = MqttConnection()
    df = DataFrame({"col1": [1, 2], "col2": [3, 4]})
    result = connection.prepare_payload_for_publish(df)
    assert isinstance(result, str)
    # DataFrame.to_json() returns a JSON string
    parsed = json.loads(result)
    assert "col1" in parsed
    assert "col2" in parsed


def test_prepare_payload_for_publish_series():
    """Test prepare_payload_for_publish with Series payload."""
    connection = MqttConnection()
    series = Series([1, 2, 3], name="test")
    result = connection.prepare_payload_for_publish(series)
    assert isinstance(result, str)


def test_prepare_payload_for_publish_string():
    """Test prepare_payload_for_publish with string payload."""
    connection = MqttConnection()
    assert connection.prepare_payload_for_publish("test") == "test"


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


# =============================================================================
# Tests for _prepare_mqtt_topic (all formats)
# =============================================================================


def test_prepare_mqtt_topic_plain_format():
    """Test _prepare_mqtt_topic with PLAIN format."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.PLAIN,
        output_entity__id_interface="TestOutput:001",
        output_attribute__id_interface="temperature",
    )
    assert topic == "encodapy/TestOutput:001/temperature"


def test_prepare_mqtt_topic_fiware_attr_format():
    """Test _prepare_mqtt_topic with FIWARE_ATTR format."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
        output_entity__id_interface="TestOutput:001",
        output_attribute__id_interface="temperature",
    )
    assert topic == "encodapy/TestOutput:001/attrs"


def test_prepare_mqtt_topic_fiware_cmdexe_format():
    """Test _prepare_mqtt_topic with FIWARE_CMDEXE format."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.FIWARE_CMDEXE,
        output_entity__id_interface="TestOutput:001",
        output_attribute__id_interface="command1",
    )
    assert topic == "encodapy/TestOutput:001/cmdexe"


def test_prepare_mqtt_topic_unsupported_format():
    """Test _prepare_mqtt_topic with unsupported format raises error."""
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encodapy")

    with pytest.raises(NotSupportedError, match="is not supported"):
        connection._prepare_mqtt_topic(
            mqtt_format="INVALID_FORMAT",
            output_entity__id_interface="TestOutput:001",
            output_attribute__id_interface="temperature",
        )


# =============================================================================
# Tests for _prepare_mqtt_payload (all formats)
# =============================================================================


def test_prepare_mqtt_payload_plain_format():
    """Test _prepare_mqtt_payload with PLAIN format."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=22.5,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity, output_attribute=output_attribute
    )
    assert payload == 22.5


def test_prepare_mqtt_payload_fiware_attr_format():
    """Test _prepare_mqtt_payload with FIWARE_ATTR format."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[],
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


def test_prepare_mqtt_payload_fiware_attr_with_timestamp():
    """Test _prepare_mqtt_payload with FIWARE_ATTR format including timestamp."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[],
    )
    timestamp = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=22.5,
        mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
        timestamp=timestamp,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity, output_attribute=output_attribute
    )
    assert isinstance(payload, dict)
    assert payload["temperature"] == 22.5
    assert "TimeInstant" in payload


def test_prepare_mqtt_payload_fiware_cmdexe_format():
    """Test _prepare_mqtt_payload with FIWARE_CMDEXE format."""
    connection = MqttConnection()
    output_entity = OutputModel(
        id="test",
        interface=Interfaces.MQTT,
        id_interface="Test:001",
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="cmd",
        id_interface="command",
        value="ON",
        mqtt_format=MQTTFormatTypes.FIWARE_CMDEXE,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity, output_attribute=output_attribute
    )
    assert isinstance(payload, dict)
    assert payload["command"] == "ON"


# =============================================================================
# Tests for subscribe_to_message_store_topics
# =============================================================================


def test_subscribe_to_message_store_topics_empty_store():
    """Test subscribe_to_message_store_topics with empty store raises error."""
    connection = MqttConnection()
    connection.mqtt_client = MagicMock()
    connection.mqtt_message_store = {}

    with pytest.raises(NotSupportedError, match="empty"):
        connection.subscribe_to_message_store_topics()


def test_subscribe_to_message_store_topics_success(mock_mqtt_connection_connected):
    """Test subscribe_to_message_store_topics subscribes to all topics."""
    mock_mqtt_connection_connected.mqtt_message_store = {
        "topic1": {"entity_id": "e1"},
        "topic2": {"entity_id": "e2"},
    }

    mock_mqtt_connection_connected.subscribe_to_message_store_topics()

    mock_mqtt_connection_connected.mqtt_client.subscribe.assert_has_calls([
        (("topic1",), {}),
        (("topic2",), {}),
    ])


# =============================================================================
# Tests for start_mqtt_client and stop_mqtt_client
# =============================================================================


def test_start_mqtt_client_no_client():
    """Test start_mqtt_client without client raises error."""
    connection = MqttConnection()
    connection.mqtt_client = None

    with pytest.raises(NotSupportedError, match="not prepared"):
        connection.start_mqtt_client()


def test_start_mqtt_client_already_running():
    """Test start_mqtt_client when already running."""
    connection = MqttConnection()
    connection.mqtt_client = MagicMock()
    connection._mqtt_loop_running = True

    connection.start_mqtt_client()
    connection.mqtt_client.loop_start.assert_not_called()


def test_start_mqtt_client_success():
    """Test start_mqtt_client sets up callbacks and starts loop."""
    connection = MqttConnection()
    connection.mqtt_client = MagicMock()
    connection._mqtt_loop_running = False

    connection.start_mqtt_client()

    assert connection._mqtt_loop_running is True
    connection.mqtt_client.loop_start.assert_called_once()
    connection.mqtt_client.reconnect_delay_set.assert_called_once()
    # Callback assignment can't be easily tested with MagicMock
    # but we can verify the method was called


def test_stop_mqtt_client_no_client():
    """Test stop_mqtt_client with no client does nothing."""
    connection = MqttConnection()
    connection.mqtt_client = None
    connection._mqtt_loop_running = False

    connection.stop_mqtt_client()
    # No error should be raised


def test_stop_mqtt_client_success():
    """Test stop_mqtt_client stops loop and disconnects."""
    connection = MqttConnection()
    # Create a mock that is an instance of mqtt.Client
    mock_client = MagicMock(spec=mqtt.Client)
    connection.mqtt_client = mock_client
    connection._mqtt_loop_running = True

    connection.stop_mqtt_client()

    assert connection._mqtt_loop_running is False
    mock_client.loop_stop.assert_called_once()
    mock_client.disconnect.assert_called_once()
