"""
Script to send different types of mqtt messages from a dummy storage to the service
"""

import json
import os
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC_PREFIX = os.environ.get("MQTT_TOPIC_PREFIX", "")

if __name__ == "__main__":
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # 1. Send "22.5 °C" as plain string to thermal_storage/t_sen_bot
    topic1 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_bot"
    payload1 = "22.5 °C"
    client.publish(topic1, payload1)
    print(f"Published to {topic1}: {payload1}")

    time.sleep(10)

    # 2. Send {"value": 20} as JSON to thermal_storage/t_sen_set
    topic2 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_set"
    payload2 = json.dumps({"value": 20})
    client.publish(topic2, payload2)
    print(f"Published to {topic2}: {payload2}")

    time.sleep(10)

    # 3. Send {"t_sen_bot": 22.5, "t_sen_set": 45} as JSON to thermal_storage
    topic3 = f"{MQTT_TOPIC_PREFIX}thermal_storage"
    payload3 = json.dumps({"t_sen_bot": 22.5, "t_sen_set": 45})
    client.publish(topic3, payload3)
    print(f"Published to {topic3}: {payload3}")

    client.disconnect()
