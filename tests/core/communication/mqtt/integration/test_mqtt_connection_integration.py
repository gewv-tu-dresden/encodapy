"""Integration tests for MQTT connection functionality in EnCoDaPy.

This module tests the MQTT connection with a real Mosquitto broker running in Docker.
Tests cover:
- Connection establishment and lifecycle
- Message publishing and receiving
- Callback functions (on_connect, on_message, on_disconnect)
- Subscription management

Test Strategy:
- Uses testcontainers to start Mosquitto broker
- Tests real MQTT interactions
- Requires Docker to be running
- Marked with @pytest.mark.integration and @pytest.mark.docker
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name, import-outside-toplevel

import time
from unittest.mock import MagicMock

import pytest

from encodapy.config import Interfaces
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
# Connection Lifecycle Tests
# =============================================================================


def test_mqtt_connection_establishment(mqtt_connection_connected):
    """Test that MQTT connection can be established with real broker."""
    assert mqtt_connection_connected._mqtt_connected is True
    assert mqtt_connection_connected.mqtt_client is not None


def test_mqtt_connection_parameters(mqtt_environment, mqtt_connection_connected):
    """Test that connection parameters are correctly set."""
    assert mqtt_connection_connected.mqtt_params.host == mqtt_environment.get("host")
    assert mqtt_connection_connected.mqtt_params.port == mqtt_environment.get("port")
    assert mqtt_connection_connected.mqtt_params.topic_prefix == \
        mqtt_environment.get("topic_prefix")


def test_mqtt_connection_message_store_initialized(mqtt_connection_connected):
    """Test that message store is initialized with input entities."""
    assert len(mqtt_connection_connected.mqtt_message_store) > 0
    assert "encodapy/test/TestEntity:001" in mqtt_connection_connected.mqtt_message_store
    assert (
        "encodapy/test/TestEntity:001/temperature"
        in mqtt_connection_connected.mqtt_message_store
    )


def test_mqtt_subscribe_to_message_store_topics(mqtt_connection_connected):
    """Test subscribing to all topics in message store."""
    # This test verifies no error is raised
    mqtt_connection_connected.subscribe_to_message_store_topics()
    # If we get here without error, the test passes


# =============================================================================
# Publish and Subscribe Tests
# =============================================================================


def test_mqtt_publish_and_receive_simple_message(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing a simple message and receiving it."""
    test_topic = mqtt_test_topics["temperature"]
    test_payload = "25.5"

    # Publish the message
    mqtt_connection_connected.publish(topic=test_topic, payload=test_payload)

    # Wait for message to be processed
    time.sleep(0.5)

    # Check that message was received and stored
    assert test_topic in mqtt_connection_connected.mqtt_message_store
    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 25.5
    assert store_item["timestamp"] is not None


def test_mqtt_publish_json_message(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing and receiving a JSON message."""
    test_topic = mqtt_test_topics["temperature"]
    test_payload = {"value": 30.0, "unit": "CEL"}

    mqtt_connection_connected.publish(topic=test_topic, payload=test_payload)
    time.sleep(0.5)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 30.0


def test_mqtt_publish_with_timestamp_key(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing message with custom timestamp key."""
    test_topic = mqtt_test_topics["temperature"]
    # Use dict payload so it gets JSON-encoded properly
    test_payload = {"value": 35.0, "TimeInstant": "2024-01-15T12:00:00+00:00"}

    mqtt_connection_connected.publish(topic=test_topic, payload=test_payload)
    time.sleep(0.5)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 35.0
    assert store_item["timestamp"] is not None


def test_mqtt_publish_numeric_with_unit(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing numeric value with unit suffix."""
    test_topic = mqtt_test_topics["temperature"]
    test_payload = "42.5 °C"

    mqtt_connection_connected.publish(topic=test_topic, payload=test_payload)
    time.sleep(0.5)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    # Should extract the numeric value
    assert store_item["value"] == 42.5


def test_mqtt_publish_to_unknown_topic(mqtt_connection_connected):
    """Test publishing to a topic not in message store."""
    unknown_topic = "encodapy/test/unknown/topic"
    test_payload = "test value"

    # Should not raise an error
    mqtt_connection_connected.publish(topic=unknown_topic, payload=test_payload)
    time.sleep(0.2)

    # Topic should not be in message store (since it wasn't subscribed)
    assert unknown_topic not in mqtt_connection_connected.mqtt_message_store


def test_mqtt_publish_dict_payload(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing a dict payload (auto-converted to JSON)."""
    test_topic = mqtt_test_topics["temperature"]
    test_payload = {"value": 40.0, "quality": "good"}

    mqtt_connection_connected.publish(topic=test_topic, payload=test_payload)
    time.sleep(0.5)

    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 40.0


# =============================================================================
# Multiple Message Tests
# =============================================================================


def test_mqtt_publish_multiple_messages(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing multiple messages to different topics."""
    topics_and_payloads = [
        (mqtt_test_topics["temperature"], "22.5"),
        (mqtt_test_topics["humidity"], "65.0"),
    ]

    for topic, payload in topics_and_payloads:
        mqtt_connection_connected.publish(topic=topic, payload=payload)
        time.sleep(0.1)

    # Verify all messages were received
    for topic, expected_value in topics_and_payloads:
        assert topic in mqtt_connection_connected.mqtt_message_store
        store_item = mqtt_connection_connected.mqtt_message_store[topic]
        assert store_item["value"] == float(expected_value)


def test_mqtt_message_ordering(mqtt_connection_connected, mqtt_test_topics):
    """Test that messages are processed in order."""
    test_topic = mqtt_test_topics["temperature"]
    values = [20.0, 21.0, 22.0, 23.0, 24.0]

    for value in values:
        mqtt_connection_connected.publish(topic=test_topic, payload=str(value))
        time.sleep(0.05)  # Small delay between messages

    # Last message should have the last value
    store_item = mqtt_connection_connected.mqtt_message_store[test_topic]
    assert store_item["value"] == 24.0


# =============================================================================
# Entity Message Tests (FIWARE-style)
# =============================================================================


def test_mqtt_publish_entity_message(mqtt_connection_connected, mqtt_test_topics):
    """Test publishing a FIWARE-style entity message."""
    entity_topic = mqtt_test_topics["entity"]
    # FIWARE entity message format
    payload = (
        '{"temperature": 28.0, "TimeInstant": "2026-01-01T00:00:00Z"}, '
        '"humidity": 55.0 , "TimeInstant": "2026-01-01T00:00:00Z"}'
    )

    mqtt_connection_connected.publish(topic=entity_topic, payload=payload)
    time.sleep(0.5)

    # The entity topic message should be stored
    assert entity_topic in mqtt_connection_connected.mqtt_message_store


# =============================================================================
# Disconnect and Reconnect Tests
# =============================================================================


def test_mqtt_disconnect_and_reconnect(mqtt_connection):
    """Test disconnecting and reconnecting to the broker."""
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
    mqtt_connection.stop_mqtt_client()
    assert mqtt_connection._mqtt_connected is False
    assert mqtt_connection._mqtt_loop_running is False

    # Reconnect
    mqtt_connection.prepare_mqtt_connection()
    assert mqtt_connection._mqtt_connection_event.wait(timeout=10)
    assert mqtt_connection._mqtt_connected is True

    # Clean up
    mqtt_connection.stop_mqtt_client()
