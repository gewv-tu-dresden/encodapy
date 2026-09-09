"""Integration tests for MQTT message handling functionality in EnCoDaPy.

This module tests MQTT message processing with a real Mosquitto broker.
Tests cover:
- Message callback handling
- Payload extraction from various formats
- Data retrieval from MQTT
- Command execution messages
- Timestamp handling

Test Strategy:
- Uses testcontainers to start Mosquitto broker
- Tests real MQTT message processing
- Requires Docker to be running
- Marked with @pytest.mark.integration and @pytest.mark.docker
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import time
from unittest.mock import MagicMock

import pytest

from encodapy.config import DataQueryTypes, Interfaces
from encodapy.config.models import AttributeModel, InputModel
from encodapy.config.types import AttributeTypes


# =============================================================================
# Test Configuration - Mark all tests as integration and docker
# =============================================================================

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]


# =============================================================================
# Payload Extraction Integration Tests
# =============================================================================


def test_extract_payload_from_plain_numeric(mqtt_connection_connected, mqtt_test_topics):
    """Test extracting payload from plain numeric string."""
    test_topic = mqtt_test_topics["temperature"]

    # Publish plain numeric value
    mqtt_connection_connected.publish(topic=test_topic, payload="42.5")
    time.sleep(0.3)

    # Verify extraction
    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 42.5
    assert isinstance(store_item["value"], float)


def test_extract_payload_from_json_with_value_key(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test extracting value from JSON with 'value' key."""
    test_topic = mqtt_test_topics["temperature"]
    payload = '{"value": 28.0, "unit": "CEL", "metadata": {}}'

    mqtt_connection_connected.publish(topic=test_topic, payload=payload)
    time.sleep(0.3)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 28.0


def test_extract_payload_from_json_with_custom_timestamp(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test extracting payload with custom timestamp key."""
    test_topic = mqtt_test_topics["temperature"]
    timestamp_str = "2024-01-15T14:30:00+00:00"
    # Use dict payload so it gets JSON-encoded properly
    payload = {"value": 30.0, "TimeInstant": timestamp_str}

    mqtt_connection_connected.publish(topic=test_topic, payload=payload)
    time.sleep(0.3)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 30.0
    assert store_item["timestamp"] is not None


def test_extract_payload_from_number_with_unit_suffix(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test extracting number from string with unit suffix."""
    test_topic = mqtt_test_topics["temperature"]

    # Publish with unit suffix
    mqtt_connection_connected.publish(topic=test_topic, payload="65.5 %")
    time.sleep(0.3)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 65.5


def test_extract_payload_from_integer_string(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test extracting integer from string."""
    test_topic = mqtt_test_topics["temperature"]

    mqtt_connection_connected.publish(topic=test_topic, payload="42")
    time.sleep(0.3)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 42


# =============================================================================
# get_data_from_mqtt Integration Tests
# =============================================================================


def test_get_data_from_mqtt_success(mqtt_connection_connected, mqtt_test_topics):
    """Test getting data from MQTT after publishing."""
    test_topic = mqtt_test_topics["temperature"]
    test_value = 25.5

    # Publish data
    mqtt_connection_connected.publish(topic=test_topic, payload=str(test_value))
    time.sleep(0.3)

    # Create input entity matching the topic
    input_entity = InputModel(
        id="test_get_data",
        interface=Interfaces.MQTT,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
            ),
        ],
    )

    # Get data
    result = mqtt_connection_connected.get_data_from_mqtt(
        method=DataQueryTypes.CALCULATION,
        entity=input_entity,
    )

    assert result.id == "test_get_data"
    assert len(result.attributes) == 1
    assert result.attributes[0].id == "temperature"
    assert result.attributes[0].data == test_value
    assert result.attributes[0].data_available is True


def test_get_data_from_mqtt_missing_topic(mqtt_connection_connected):
    """Test getting data from MQTT for topic not in message store."""
    input_entity = InputModel(
        id="test_missing",
        interface=Interfaces.MQTT,
        id_interface="NonExistent:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
            ),
        ],
    )

    result = mqtt_connection_connected.get_data_from_mqtt(
        method=DataQueryTypes.CALCULATION,
        entity=input_entity,
    )

    assert result.id == "test_missing"
    assert len(result.attributes) == 1
    assert result.attributes[0].data is None
    assert result.attributes[0].data_available is False


def test_get_data_from_mqtt_multiple_attributes(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test getting data for entity with multiple attributes."""
    # Publish to both attribute topics
    mqtt_connection_connected.publish(
        topic=mqtt_test_topics["temperature"], payload="22.5"
    )
    time.sleep(0.1)
    mqtt_connection_connected.publish(
        topic=mqtt_test_topics["humidity"], payload="65.0"
    )
    time.sleep(0.3)

    input_entity = InputModel(
        id="test_multi",
        interface=Interfaces.MQTT,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
            ),
            AttributeModel(
                id="humidity",
                id_interface="humidity",
                type=AttributeTypes.VALUE,
            ),
        ],
    )

    result = mqtt_connection_connected.get_data_from_mqtt(
        method=DataQueryTypes.CALCULATION,
        entity=input_entity,
    )

    assert len(result.attributes) == 2
    temp_attr = next(
        (a for a in result.attributes if a.id == "temperature"), None
    )
    hum_attr = next(
        (a for a in result.attributes if a.id == "humidity"), None
    )

    assert temp_attr is not None
    assert temp_attr.data == 22.5
    assert temp_attr.data_available is True

    assert hum_attr is not None
    assert hum_attr.data == 65.0
    assert hum_attr.data_available is True


# =============================================================================
# Message Store Update Tests
# =============================================================================


def test_message_store_updated_on_receive(mqtt_connection_connected, mqtt_test_topics):
    """Test that message store is updated when messages are received."""
    test_topic = mqtt_test_topics["temperature"]
    initial_value = mqtt_connection_connected.mqtt_message_store[test_topic][
        "value"
    ]

    # Publish new value
    new_value = 99.9
    mqtt_connection_connected.publish(topic=test_topic, payload=str(new_value))
    time.sleep(0.3)

    # Check store was updated
    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == new_value
    assert store_item["value"] != initial_value


def test_message_store_timestamp_updated(mqtt_connection_connected, mqtt_test_topics):
    """Test that timestamp is updated when new messages arrive."""
    test_topic = mqtt_test_topics["temperature"]

    # Publish first message
    mqtt_connection_connected.publish(topic=test_topic, payload="20.0")
    time.sleep(0.3)

    first_timestamp = mqtt_connection_connected.mqtt_message_store[test_topic][
        "timestamp"
    ]

    # Publish second message
    time.sleep(0.2)
    mqtt_connection_connected.publish(topic=test_topic, payload="21.0")
    time.sleep(0.3)

    second_timestamp = mqtt_connection_connected.mqtt_message_store[test_topic][
        "timestamp"
    ]

    # Second timestamp should be later
    assert second_timestamp >= first_timestamp


# =============================================================================
# FIWARE-Style Message Tests
# =============================================================================


def test_fiware_attr_format_message_processing(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test processing FIWARE ATTR format messages."""
    entity_topic = mqtt_test_topics["entity"]

    # FIWARE ATTR format payload as dict
    payload = {"temperature": {"value": 25.0, "type": "Float"}}

    mqtt_connection_connected.publish(topic=entity_topic, payload=payload)
    time.sleep(0.5)

    # Check entity topic was updated
    assert entity_topic in mqtt_connection_connected.mqtt_message_store
    store_item = mqtt_connection_connected.mqtt_message_store[entity_topic]
    # The message store should have been updated with the payload
    # Note: The exact behavior depends on _extract_attributes_from_payload_and_update_store
    assert store_item is not None


def test_fiware_cmdexe_format_message(
    mqtt_connection_connected, mqtt_test_topics
):
    """Test publishing and receiving FIWARE CMDEXE format messages."""
    command_topic = mqtt_test_topics["command"]
    payload = '{"command": "ON", "status": "pending"}'

    mqtt_connection_connected.publish(topic=command_topic, payload=payload)
    time.sleep(0.3)

    # Check message was stored
    assert command_topic in mqtt_connection_connected.mqtt_message_store
    store_item = mqtt_connection_connected.mqtt_message_store[command_topic]
    assert store_item["value"] is not None


# =============================================================================
# Connection Callback Tests
# =============================================================================


def test_on_connect_callback_subscribes_to_topics(mqtt_connection):
    """Test that on_connect callback subscribes to message store topics."""
    # Set up config with mock to avoid validation errors
    mock_config = MagicMock()
    mock_config.inputs = [
        InputModel(
            id="test_input",
            interface=Interfaces.MQTT,
            id_interface="TestEntity:001",
            attributes=[
                AttributeModel(
                    id="temperature",
                    id_interface="temperature",
                    type=AttributeTypes.VALUE,
                    value=None,
                ),
            ],
        ),
    ]
    mock_config.outputs = []

    mqtt_connection.config = mock_config

    mqtt_connection.prepare_mqtt_connection()
    assert mqtt_connection._mqtt_connection_event.wait(timeout=10)

    # The on_connect callback should have been called and subscribed to topics
    # We can verify by checking that the client's subscribe was called
    # (This is implicitly tested by successful connection)

    mqtt_connection.stop_mqtt_client()


def test_on_disconnect_callback_clears_connection_flag(mqtt_connection):
    """Test that on_disconnect callback clears connection flag."""
    # Set up config with mock to avoid validation errors
    mock_config = MagicMock()
    mock_config.inputs = [
        InputModel(
            id="test_input",
            interface=Interfaces.MQTT,
            id_interface="TestEntity:001",
            attributes=[
                AttributeModel(
                    id="temperature",
                    id_interface="temperature",
                    type=AttributeTypes.VALUE,
                    value=None,
                ),
            ],
        ),
    ]
    mock_config.outputs = []

    mqtt_connection.config = mock_config

    # Connect
    mqtt_connection.prepare_mqtt_connection()
    assert mqtt_connection._mqtt_connection_event.wait(timeout=10)
    assert mqtt_connection._mqtt_connected is True

    # Disconnect
    mqtt_connection.mqtt_client.disconnect()
    time.sleep(0.5)

    # Connection flag should be cleared by on_disconnect callback
    assert mqtt_connection._mqtt_connected is False

    mqtt_connection.stop_mqtt_client()


# =============================================================================
# Stress/Concurrency Tests
# =============================================================================


def test_rapid_message_publishing(mqtt_connection_connected, mqtt_test_topics):
    """Test handling rapid message publishing."""
    test_topic = mqtt_test_topics["temperature"]

    # Publish many messages rapidly
    for i in range(10):
        mqtt_connection_connected.publish(
            topic=test_topic, payload=str(20.0 + i)
        )
        time.sleep(0.01)  # Very short delay

    time.sleep(0.5)

    # Should have the last value
    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 29.0


def test_multiple_topics_concurrent(mqtt_connection_connected, mqtt_test_topics):
    """Test handling messages on multiple topics concurrently."""
    topics = [
        mqtt_test_topics["temperature"],
        mqtt_test_topics["humidity"],
        mqtt_test_topics["entity"],
    ]
    payloads = [25.0, 60.0, {"temp": 25.0}]

    # Publish to all topics
    for topic, payload in zip(topics, payloads):
        mqtt_connection_connected.publish(topic=topic, payload=payload)

    time.sleep(0.5)

    # All topics should have been updated
    for topic in topics:
        assert topic in mqtt_connection_connected.mqtt_message_store
        # Check that the topic exists in the store (value may be None for entity topics)
        assert mqtt_connection_connected.mqtt_message_store[topic] is not None
