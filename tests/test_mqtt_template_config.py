"""Tests for MQTT topic and payload template rendering."""

import json

from encodapy.config.mqtt_messages_template import MQTTTemplateConfig


def test_topic_template_replaces_embedded_placeholders() -> None:
    """Topic templates replace all embedded placeholders with runtime values."""

    template = MQTTTemplateConfig(
        topic="__MQTT_TOPIC_PREFIX__/develop/__OUTPUT_ENTITY__/__OUTPUT_ATTRIBUTE__",
        payload={"value": "__OUTPUT_VALUE__"},
    )

    topic = template.topic.render(
        output_entity="building_1",
        output_attribute="temperature",
        mqtt_topic_prefix="encoda",
    )

    assert topic == "encodapy/develop/building_1/temperature"


def test_payload_template_keeps_native_type_for_exact_placeholder() -> None:
    """Exact payload placeholders preserve native JSON scalar types."""

    template = MQTTTemplateConfig(
        topic="out",
        payload={
            "value": "__OUTPUT_VALUE__",
            "label": "sensor __OUTPUT_ATTRIBUTE__",
        },
    )

    payload = template.payload.render(
        output_entity="building_1",
        output_attribute="temperature",
        output_value=42,
        output_unit="degC",
        output_time=None,
        mqtt_topic_prefix="encoda",
    )
    payload_dict = json.loads(payload)

    assert payload_dict["value"] == 42
    assert payload_dict["label"] == "sensor temperature"
