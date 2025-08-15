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
    TOPIC_1 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_bot"
    PAYLOAD_1 = "22.5 °C"
    client.publish(TOPIC_1, PAYLOAD_1)
    print(f"Published to {TOPIC_1}: {PAYLOAD_1}")

    time.sleep(10)

    # 2. Send {"value": 20} as JSON to thermal_storage/t_sen_set
    TOPIC_2 = f"{MQTT_TOPIC_PREFIX}thermal_storage/t_sen_set"
    PAYLOAD_2 = json.dumps({"value": 20})
    client.publish(TOPIC_2, PAYLOAD_2)
    print(f"Published to {TOPIC_2}: {PAYLOAD_2}")

    time.sleep(10)

    # 3. Send {"t_sen_bot": 22.5, "t_sen_set": 45} as JSON to thermal_storage
    TOPIC_3 = f"{MQTT_TOPIC_PREFIX}thermal_storage"
    PAYLOAD_3 = json.dumps({"t_sen_bot": 22.5, "t_sen_set": 45})
    client.publish(TOPIC_3, PAYLOAD_3)
    print(f"Published to {TOPIC_3}: {PAYLOAD_3}")

    client.disconnect()
