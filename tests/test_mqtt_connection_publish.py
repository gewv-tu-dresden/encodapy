import json
from datetime import datetime, timezone

from encodapy.config import (
    AttributeModel,
    Interfaces,
    MQTTEnvVariables,
    MQTTFormatTypes,
    OutputModel,
)
from encodapy.config.mqtt_messages_template import MQTTTemplateConfig
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.units import DataUnits


def test_send_data_to_mqtt_renders_template_and_calls_publish() -> None:
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encoda")
    connection.config = object()  # type: ignore[assignment]
    connection.mqtt_client = object()  # prevent pre-check from failing
    connection._mqtt_connected = True

    template = MQTTTemplateConfig(
        topic="__MQTT_TOPIC_PREFIX__/__OUTPUT_ENTITY__/__OUTPUT_ATTRIBUTE__",
        payload={
            "DATAPOINT": "__OUTPUT_ATTRIBUTE__",
            "VALUE": "__OUTPUT_VALUE__",
            "UNIT": "__OUTPUT_UNIT__",
            "TIME": "__OUTPUT_TIME__",
        },
        time_format="%Y-%m-%dT%H:%M:%SZ",
    )

    output_entity = OutputModel(
        id="entity_1",
        id_interface="heatpump",
        interface=Interfaces.MQTT,
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=21.5,
        unit=DataUnits.DEGREECELSIUS,
        timestamp=datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc),
        mqtt_format=template,
    )

    published: list[tuple[str, str]] = []

    def capture_publish(topic: str, payload: str) -> None:
        published.append((topic, payload))

    connection.publish = capture_publish  # type: ignore[method-assign]

    connection.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=[output_attribute],
    )

    assert len(published) == 1
    topic, payload = published[0]
    assert topic == "encoda/heatpump/temperature"
    payload_dict = json.loads(payload)
    assert payload_dict == {
        "DATAPOINT": "temperature",
        "VALUE": 21.5,
        "UNIT": "CEL",
        "TIME": "2026-04-28T12:00:00Z",
    }


def test_send_data_to_mqtt_skips_none_values_if_enabled() -> None:
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(
        topic_prefix="encoda",
        skip_none_values=True,
    )
    connection.config = object()  # type: ignore[assignment]
    connection.mqtt_client = object()  # prevent pre-check from failing
    connection._mqtt_connected = True

    output_entity = OutputModel(
        id="entity_1",
        id_interface="heatpump",
        interface=Interfaces.MQTT,
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="temp",
        id_interface="temperature",
        value=None,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )

    published: list[tuple[str, object]] = []

    def capture_publish(topic: str, payload: object) -> None:
        published.append((topic, payload))

    connection.publish = capture_publish  # type: ignore[method-assign]

    connection.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=[output_attribute],
    )

    assert published == []


def test_send_data_to_mqtt_without_template_uses_plain_topic_and_payload() -> None:
    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(topic_prefix="encoda")
    connection.config = object()  # type: ignore[assignment]
    connection.mqtt_client = object()  # prevent pre-check from failing
    connection._mqtt_connected = True

    output_entity = OutputModel(
        id="entity_1",
        id_interface="heatpump",
        interface=Interfaces.MQTT,
        attributes=[],
    )
    output_attribute = AttributeModel(
        id="power",
        id_interface="power",
        value=123.4,
        mqtt_format=MQTTFormatTypes.PLAIN,
    )

    published: list[tuple[str, object]] = []

    def capture_publish(topic: str, payload: object) -> None:
        published.append((topic, payload))

    connection.publish = capture_publish  # type: ignore[method-assign]

    connection.send_data_to_mqtt(
        output_entity=output_entity,
        output_attributes=[output_attribute],
    )

    assert len(published) == 1
    topic, payload = published[0]
    assert topic == "encoda/heatpump/power"
    assert payload == 123.4
