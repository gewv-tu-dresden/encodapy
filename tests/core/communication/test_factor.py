"""Tests for the optional `factor` key on attributes (Issue #92).

This module tests the central scaling helper `apply_factor` and the
application of the attribute `factor` in all communication connections
(MQTT, FILE) in both directions (input and output).

Test Strategy:
- Unit tests for the helper with numeric and non-numeric values
- Unit tests for the MQTT output payload scaling (plain and template format)
- Unit test for the MQTT input data scaling (message store)
- Unit test for the FILE output scaling (send_data_to_json_file)
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name
import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock

from encodapy.config import MQTTFormatTypes
from encodapy.config.models import (
    AttributeModel,
)
from encodapy.config.mqtt_messages_template import MQTTTemplateConfig
from encodapy.service.communication.file_connection import FileConnection
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.models import apply_factor


class TestApplyFactor:
    """Tests for the central apply_factor helper."""

    def test_numeric_value_is_scaled(self):
        """Numeric values are multiplied by the factor."""
        assert apply_factor(1234, 0.1) == 123.4

    def test_negative_factor(self):
        """Negative factors are supported."""
        assert apply_factor(10, -2) == -20

    def test_default_factor_one_is_identity(self):
        """Factor 1.0 (the default) returns the value unchanged."""
        assert apply_factor(42, 1.0) == 42

    def test_bool_is_not_scaled(self):
        """Booleans are returned unchanged (bool is a subclass of int)."""
        assert apply_factor(True, 0.1) is True

    def test_string_is_not_scaled(self):
        """String values are returned unchanged."""
        assert apply_factor("42.0 °C", 0.1) == "42.0 °C"

    def test_none_is_not_scaled(self):
        """None is returned unchanged."""
        assert apply_factor(None, 0.1) is None


class TestMqttFactor:
    """Tests for the `factor` key applied in the MQTT connection."""

    def test_prepare_mqtt_payload_plain_with_factor(self):
        """PLAIN output payload is scaled by the attribute factor."""
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        attribute = AttributeModel(
            id="temperature",
            value=1000,
            mqtt_format=MQTTFormatTypes.PLAIN,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id_interface = "TestOutput:001"
        assert connection._prepare_mqtt_payload(entity, attribute) == 100.0

    def test_prepare_mqtt_payload_template_with_factor(self):
        """Template output payload receives the scaled value."""
        template = MQTTTemplateConfig.model_validate(
            {
                "topic": "{{mqtt_topic_prefix}}/{{output_entity}}/{{output_attribute}}",
                "payload": {"value": "{{output_value}}"},
            }
        )
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        attribute = AttributeModel(
            id="temperature",
            value=1000,
            mqtt_format=template,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id_interface = "TestOutput:001"
        assert "100.0" in connection._prepare_mqtt_payload(entity, attribute)

    def test_get_data_from_mqtt_with_factor(self):
        """Incoming values are multiplied by the attribute factor."""
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        connection.mqtt_message_store = {
            "test/TestInput:001/temperature": {
                "entity_id": "TestInput:001",
                "attribute_id": "temperature",
                "value": 1000,
                "unit": None,
                "timestamp": datetime(2025, 1, 1, tzinfo=UTC),
            }
        }
        attribute = AttributeModel(
            id="temperature",
            id_interface="temperature",
            value=None,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id = "TestInput:001"
        entity.id_interface = "TestInput:001"
        entity.attributes = [attribute]
        result = connection.get_data_from_mqtt(method=MagicMock(), entity=entity)
        assert result.attributes[0].data == 100.0


class TestFileFactor:
    """Tests for the `factor` key applied in the FILE connection."""

    def test_send_data_to_json_file_with_factor(self, tmp_path):
        """Output values written to JSON files are scaled by the factor."""
        connection = FileConnection()
        connection.file_params = MagicMock()
        connection.file_params.path_of_results = str(tmp_path)
        output_entity = MagicMock()
        output_entity.id = "test_entity"
        attribute = AttributeModel(
            id="result",
            id_interface="result",
            value=1000,
            factor=0.1,
        )
        connection.send_data_to_json_file(
            output_entity=output_entity,
            output_attributes=[attribute],
            output_commands=[],
        )
        output_file = os.path.join(tmp_path, "outputs_test_entity.json")
        assert os.path.exists(output_file)
        with open(output_file, encoding="utf-8") as file_handle:
            content = json.load(file_handle)
        assert content[0]["attributes"][0]["value"] == 100.0
