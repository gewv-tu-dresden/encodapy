"""
Script to send different types of mqtt messages from a dummy storage to the service
"""

import json
import os
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC_PREFIX = os.environ.get("MQTT_TOPIC_PREFIX", "")

if __name__ == "__main__":
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

    client.connect(MQTT_HOST, MQTT_PORT, 60)

    # 1. Send "55.5 °C" as plain string to thermal_storage/t_sen_bot
    TOPIC1 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_bot"
    PAYLOAD1 = "55.5 °C"
    client.publish(TOPIC1, PAYLOAD1)
    print(f"Published to {TOPIC1}: {PAYLOAD1}")

    time.sleep(10)

    # 2. Send {"VALUE": 65} (value is not case-sensitive) as JSON to thermal_storage/t_sen_set
    TOPIC2 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_set"
    PAYLOAD2 = json.dumps({"VALUE": 65})
    client.publish(TOPIC2, PAYLOAD2)
    print(f"Published to {TOPIC2}: {PAYLOAD2}")

    time.sleep(10)

    # 3. Send {"t_sen_bot": 22.5, "t_sen_set": "50"} as JSON to thermal_storage,
    # even different value types are possible (Number as string will be converted automatically)
    TOPIC3 = f"{MQTT_TOPIC_PREFIX}thermal_storage"
    PAYLOAD3 = json.dumps({"t_sen_bot": 22.5, "t_sen_set": "50 °C"}, ensure_ascii=False)
    client.publish(TOPIC3, PAYLOAD3)
    print(f"Published to {TOPIC3}: {PAYLOAD3}")

    client.disconnect()
