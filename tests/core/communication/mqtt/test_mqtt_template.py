"""Template-based unit tests for MQTT connection in EnCoDaPy.

This module provides tests for template-based MQTT functionality in MqttConnection,
focusing on:
- send_data_to_mqtt (main publishing logic)
- Template-based payload/topic generation (MQTTTemplateConfig)
- Error handling in prepare_payload_for_publish

Test Strategy:
- Unit tests with mocked dependencies (paho.mqtt.client)
- Focus on template-based methods and critical paths
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name, import-outside-toplevel, missing-class-docstring, too-few-public-methods, unnecessary-lambda-assignment

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from encodapy.config import (
    Interfaces,
    MQTTFormatTypes,
    MQTTTemplateConfig,
    OutputModel,
)
from encodapy.config.models import AttributeModel
from encodapy.config.types import AttributeTypes
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.error_handling import ConfigError, NotSupportedError
from encodapy.utils.units import DataUnits


# =============================================================================
# Fixtures for Priority 1 Tests
# =============================================================================

@pytest.fixture
def mock_mqtt_connection_with_config():
    """Create a mock MqttConnection instance with minimal valid config."""
    connection = MqttConnection()

    # Create minimal mock config
    mock_config = MagicMock()
    mock_config.inputs = []
    mock_config.outputs = []
    connection.config = mock_config

    connection.mqtt_params = MagicMock()
    connection.mqtt_params.host = "test.broker"
    connection.mqtt_params.port = 1883
    connection.mqtt_params.topic_prefix = "test"
    connection.mqtt_params.skip_none_values = False
    connection.mqtt_params.publish_delay = 0.0

    # Mock the MQTT client
    connection.mqtt_client = MagicMock()
    connection._mqtt_connected = True

    return connection


# =============================================================================
# Helper Functions (not fixtures, to avoid pytest fixture direct call issues)
# =============================================================================


def _create_output_entity():
    """Create a mock output entity for testing."""
    return OutputModel(
        id="test_output",
        interface=Interfaces.MQTT,
        id_interface="TestOutput:001",
        attributes=[],
    )


def _create_attribute_plain(value=25.5):
    """Create a mock attribute with PLAIN format."""
    return AttributeModel(
        id="temperature",
        id_interface="temperature",
        type=AttributeTypes.VALUE,
        value=value,
        unit=None,
        timestamp=None,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )


def _create_attribute_with_none_value():
    """Create a mock attribute with None value."""
    return AttributeModel(
        id="empty_attr",
        id_interface="empty",
        type=AttributeTypes.VALUE,
        value=None,
        unit=None,
        timestamp=None,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )


# =============================================================================
# send_data_to_mqtt Tests (Zeilen 868-891) - HÖCHSTE PRIORITÄT
# =============================================================================


def test_send_data_to_mqtt_no_config(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt raises ConfigError when config is None."""
    mock_mqtt_connection_with_config.config = None

    output_entity = _create_output_entity()
    output_attributes = [_create_attribute_plain()]

    with pytest.raises(ConfigError):
        mock_mqtt_connection_with_config.send_data_to_mqtt(
            output_entity=output_entity,
            output_attributes=output_attributes,
        )


def test_send_data_to_mqtt_no_client(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt raises NotSupportedError when client is None."""
    mock_mqtt_connection_with_config.mqtt_client = None

    output_entity = _create_output_entity()
    output_attributes = [_create_attribute_plain()]

    with pytest.raises(NotSupportedError):
        mock_mqtt_connection_with_config.send_data_to_mqtt(
            output_entity=output_entity,
            output_attributes=output_attributes,
        )


def test_send_data_to_mqtt_not_connected(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt logs warning and returns when not connected."""
    mock_mqtt_connection_with_config._mqtt_connected = False

    output_entity = _create_output_entity()
    output_attributes = [_create_attribute_plain()]

    # Should not raise, but log warning and return
    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    # Verify publish was NOT called
    mock_mqtt_connection_with_config.mqtt_client.publish.assert_not_called()


def test_send_data_to_mqtt_publishes_all_attributes(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt publishes all attributes."""
    output_entity = _create_output_entity()
    output_attributes = [
        _create_attribute_plain(),
        AttributeModel(
            id="humidity",
            id_interface="humidity",
            type=AttributeTypes.VALUE,
            value=60.0,
            unit=None,
            timestamp=None,
            mqtt_format=MQTTFormatTypes.PLAIN,
        ),
    ]

    # Mock _prepare_mqtt_topic and _prepare_mqtt_payload
    mock_mqtt_connection_with_config._prepare_mqtt_topic = MagicMock(
        return_value="test/TestOutput:001/temperature"
    )
    mock_mqtt_connection_with_config._prepare_mqtt_payload = MagicMock(
        return_value="25.5"
    )

    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    # Verify publish was called twice (once per attribute)
    assert mock_mqtt_connection_with_config.mqtt_client.publish.call_count == 2


def test_send_data_to_mqtt_skip_none_values(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt skips attributes with None value when skip_none_values=True."""
    mock_mqtt_connection_with_config.mqtt_params.skip_none_values = True

    output_entity = _create_output_entity()
    output_attributes = [
        _create_attribute_plain(),  # value=25.5
        _create_attribute_with_none_value(),  # value=None
    ]

    mock_mqtt_connection_with_config._prepare_mqtt_topic = MagicMock(
        side_effect=["test/TestOutput:001/temperature", "test/TestOutput:001/empty"]
    )
    mock_mqtt_connection_with_config._prepare_mqtt_payload = MagicMock(
        side_effect=["25.5", "None"]
    )

    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    # Only the first attribute (with value) should be published
    assert mock_mqtt_connection_with_config.mqtt_client.publish.call_count == 1

    # Verify the call was for the first attribute
    call_args = mock_mqtt_connection_with_config.mqtt_client.publish.call_args_list[0]
    assert call_args[0][0] == "test/TestOutput:001/temperature"
    assert call_args[0][1] == "25.5"


def test_send_data_to_mqtt_error_handling_value_error(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt handles ValueError during publish."""
    output_entity = _create_output_entity()
    output_attributes = [_create_attribute_plain()]

    # Mock _prepare_mqtt_topic to return a valid topic
    mock_mqtt_connection_with_config._prepare_mqtt_topic = MagicMock(
        return_value="test/TestOutput:001/temperature"
    )

    # Mock _prepare_mqtt_payload to return a valid payload
    mock_mqtt_connection_with_config._prepare_mqtt_payload = MagicMock(
        return_value="25.5"
    )

    # Mock publish to raise ValueError
    mock_mqtt_connection_with_config.mqtt_client.publish.side_effect = ValueError("Test error")

    # Should not raise, but log error and continue
    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    # Verify publish was called once
    assert mock_mqtt_connection_with_config.mqtt_client.publish.call_count == 1


def test_send_data_to_mqtt_error_handling_key_error(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt handles KeyError during publish."""
    output_entity = _create_output_entity()
    output_attributes = [_create_attribute_plain()]

    mock_mqtt_connection_with_config._prepare_mqtt_topic = MagicMock(
        return_value="test/TestOutput:001/temperature"
    )
    mock_mqtt_connection_with_config._prepare_mqtt_payload = MagicMock(
        return_value="25.5"
    )

    # Mock publish to raise KeyError
    mock_mqtt_connection_with_config.mqtt_client.publish.side_effect = KeyError("test_key")

    # Should not raise, but log error and continue
    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    assert mock_mqtt_connection_with_config.mqtt_client.publish.call_count == 1


def test_send_data_to_mqtt_error_handling_not_supported_error(mock_mqtt_connection_with_config):
    """Test send_data_to_mqtt handles NotSupportedError during publish."""
    output_entity = OutputModel(
        id="test_output",
        interface=Interfaces.MQTT,
        id_interface="TestOutput:001",
        attributes=[],
    )
    output_attributes = [
        AttributeModel(
            id="temperature",
            id_interface="temperature",
            type=AttributeTypes.VALUE,
            value=25.5,
            unit=None,
            timestamp=None,
            mqtt_format=MQTTFormatTypes.PLAIN,
        )
    ]

    mock_mqtt_connection_with_config._prepare_mqtt_topic = MagicMock(
        return_value="test/TestOutput:001/temperature"
    )
    mock_mqtt_connection_with_config._prepare_mqtt_payload = MagicMock(
        side_effect=NotSupportedError("Test error")
    )

    # Should not raise, but log error and continue
    mock_mqtt_connection_with_config.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=output_attributes,
    )

    # Verify publish was NOT called (error occurred before)
    mock_mqtt_connection_with_config.mqtt_client.publish.assert_not_called()


# =============================================================================
# Template-based Payload/Topic Tests (Zeilen 752-780, 828)
# =============================================================================


def test_prepare_mqtt_payload_template_config():
    """Test _prepare_mqtt_payload with MQTTTemplateConfig."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "test"

    # Create a template config
    template_config = MQTTTemplateConfig(
        payload=("Entity: {{output_entity}}, Attribute: {{output_attribute}}, "
                   "Value: {{output_value}}"),
        topic="test/{{output_entity}}/{{output_attribute}}",
        time_format="%Y-%m-%dT%H:%M:%S%z",
        payload_embedded_placeholders=["output_entity", "output_attribute", "output_value"],
    )

    output_entity = OutputModel(
        id="test_output",
        interface=Interfaces.MQTT,
        id_interface="TestOutput:001",
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        type=AttributeTypes.VALUE,
        value=25.5,
        unit=None,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        mqtt_format=template_config,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity,
        output_attribute=output_attribute,
    )

    # Verify payload was rendered from template
    assert isinstance(payload, str)
    assert "TestOutput:001" in payload
    assert "temperature" in payload
    assert "25.5" in payload


def test_prepare_mqtt_payload_template_with_unit():
    """Test _prepare_mqtt_payload with template and unit."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "test"

    template_config = MQTTTemplateConfig(
        payload="Value: {{output_value}} {{output_unit}}",
        topic="test/{{output_entity}}",
        time_format="%Y-%m-%dT%H:%M:%S%z",
        payload_embedded_placeholders=["output_value", "output_unit"],
    )

    output_entity = _create_output_entity()
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        type=AttributeTypes.VALUE,
        value=25.5,
        unit=DataUnits.DEGREECELSIUS,  # Use DataUnits enum directly
        timestamp=None,
        mqtt_format=template_config,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity,
        output_attribute=output_attribute,
    )

    assert isinstance(payload, str)
    assert "25.5" in payload
    assert "CEL" in payload


def test_prepare_mqtt_payload_template_with_time():
    """Test _prepare_mqtt_payload with template and timestamp."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "test"

    template_config = MQTTTemplateConfig(
        payload="Time: {{output_time}}",
        topic="test/{{output_entity}}",
        time_format="%Y-%m-%d",
        payload_embedded_placeholders=["output_time"],
    )

    output_entity = OutputModel(
        id="test_output",
        interface=Interfaces.MQTT,
        id_interface="TestOutput:001",
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        type=AttributeTypes.VALUE,
        value=25.5,
        unit=None,
        timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        mqtt_format=template_config,
    )

    payload = connection._prepare_mqtt_payload(
        output_entity=output_entity,
        output_attribute=output_attribute,
    )

    assert isinstance(payload, str)
    assert "2024-01-15" in payload


def test_prepare_mqtt_payload_unsupported_format():
    """Test _prepare_mqtt_payload raises NotSupportedError for unsupported format."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()

    output_entity = _create_output_entity()

    # Create a mock format that is not supported
    # We need to bypass Pydantic validation, so we create the attribute with a valid format
    # and then patch the mqtt_format
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        type=AttributeTypes.VALUE,
        value=25.5,
        unit=None,
        timestamp=None,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )

    # Patch the mqtt_format to an unsupported value AFTER creation
    output_attribute.mqtt_format = "INVALID_FORMAT"

    with pytest.raises(NotSupportedError):
        connection._prepare_mqtt_payload(
            output_entity=output_entity,
            output_attribute=output_attribute,
        )


def test_prepare_mqtt_topic_template():
    """Test _prepare_mqtt_topic with MQTTTemplateConfig."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "encodapy"

    template_config = MQTTTemplateConfig(
        payload="",
        topic="{{mqtt_topic_prefix}}/{{output_entity}}/{{output_attribute}}",
        time_format="%Y-%m-%dT%H:%M:%S%z",
        payload_embedded_placeholders=[],
    )

    topic = connection._prepare_mqtt_topic(
        mqtt_format=template_config,
        output_entity__id_interface="TestEntity:001",
        output_attribute__id_interface="temperature",
    )

    assert topic == "encodapy/TestEntity:001/temperature"


def test_prepare_mqtt_topic_plain():
    """Test _prepare_mqtt_topic with PLAIN format."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "encodapy"

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.PLAIN,
        output_entity__id_interface="TestEntity:001",
        output_attribute__id_interface="temperature",
    )

    assert topic == "encodapy/TestEntity:001/temperature"


def test_prepare_mqtt_topic_fiware_attr():
    """Test _prepare_mqtt_topic with FIWARE_ATTR format."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "encodapy"

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
        output_entity__id_interface="TestEntity:001",
        output_attribute__id_interface="temperature",
    )

    assert topic == "encodapy/TestEntity:001/attrs"


def test_prepare_mqtt_topic_fiware_cmdexe():
    """Test _prepare_mqtt_topic with FIWARE_CMDEXE format."""
    connection = MqttConnection()
    connection.mqtt_params = MagicMock()
    connection.mqtt_params.topic_prefix = "encodapy"

    topic = connection._prepare_mqtt_topic(
        mqtt_format=MQTTFormatTypes.FIWARE_CMDEXE,
        output_entity__id_interface="TestEntity:001",
        output_attribute__id_interface="command",
    )

    assert topic == "encodapy/TestEntity:001/cmdexe"


# =============================================================================
# Error Handling in prepare_payload_for_publish (Zeilen 334-344)
# =============================================================================


def test_prepare_payload_for_publish_unsupported_type():
    """Test prepare_payload_for_publish with unsupported type (e.g., function)."""
    connection = MqttConnection()

    # Function is an unsupported type
    def sample_function(x):
        return x + 1

    payload = sample_function

    result = connection.prepare_payload_for_publish(payload)

    # Should return None and log warning
    assert result is None


def test_prepare_payload_for_publish_unsupported_object():
    """Test prepare_payload_for_publish with unsupported object type."""
    connection = MqttConnection()

    # Custom class instance is an unsupported type
    class CustomClass:  # pylint: disable=too-few-public-methods
        """Custom class for testing unsupported payload types."""

    payload = CustomClass()

    result = connection.prepare_payload_for_publish(payload)

    # Should return None and log warning
    assert result is None


def test_prepare_payload_for_publish_type_error():
    """Test prepare_payload_for_publish handles TypeError during conversion."""
    connection = MqttConnection()

    # Create a mock object that raises TypeError when str() is called
    class BadStrClass:  # pylint: disable=too-few-public-methods
        """Class that raises TypeError on str() conversion."""

        def __str__(self):
            raise TypeError("Cannot convert to string")

    payload = BadStrClass()

    result = connection.prepare_payload_for_publish(payload)

    # Should return None and log warning
    assert result is None


def test_prepare_payload_for_publish_dict():
    """Test prepare_payload_for_publish with dict payload."""
    connection = MqttConnection()

    payload = {"temperature": 25.5, "unit": "CEL"}

    result = connection.prepare_payload_for_publish(payload)

    # Should be JSON string
    assert result == '{"temperature": 25.5, "unit": "CEL"}'


def test_prepare_payload_for_publish_list():
    """Test prepare_payload_for_publish with list payload."""
    connection = MqttConnection()

    payload = [1, 2, 3, 4, 5]

    result = connection.prepare_payload_for_publish(payload)

    # Should be JSON string
    assert result == "[1, 2, 3, 4, 5]"


def test_prepare_payload_for_publish_none():
    """Test prepare_payload_for_publish with None payload."""
    connection = MqttConnection()

    result = connection.prepare_payload_for_publish(None)

    # Should return None
    assert result is None
