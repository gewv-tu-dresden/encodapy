"""
Integration test fixtures for MQTT Docker-based testing.

This module provides fixtures for integration tests that require real MQTT
services running in Docker containers. It re-exports fixtures from the docker
conftest and adds MQTT-specific fixtures.

Requires:
- Docker containers running (via testcontainers)
- testcontainers package installed
- Mosquitto broker available in the FIWARE docker compose stack
"""

# pylint: disable=redefined-outer-name, unused-import, import-outside-toplevel, protected-access

import time
import socket
from unittest.mock import MagicMock

import pytest

from encodapy.config import Interfaces
from encodapy.config.models import AttributeModel, InputModel
from encodapy.config.types import AttributeTypes
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.config.env_values import MQTTEnvVariables

from tests.docker.conftest import fiware_environment


pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]


# =============================================================================
# MQTT Environment Fixtures (using central Docker stack)
# =============================================================================


@pytest.fixture(scope="session")
def mqtt_environment(fiware_environment):  # pylint: disable=unused-argument
    """
    Fixture providing MQTT broker connection parameters.
    Uses the Mosquitto instance from the central FIWARE docker compose stack.

    Yields:
        dict: MQTT connection parameters
    """
    # Mosquitto is already running as part of the FIWARE stack
    # Check if MQTT broker is reachable
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            # Try to connect to MQTT port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((fiware_environment["mqtt_host"],
                                      int(fiware_environment["mqtt_port"])))
            sock.close()
            if result == 0:
                break
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass
        time.sleep(1)
    else:
        raise TimeoutError(
            f"MQTT broker not available after {max_attempts} attempts. "
            "Please ensure Docker is running and the FIWARE stack is started."
        )

    # Additional wait for full initialization
    time.sleep(2)

    yield {
        "host": fiware_environment["mqtt_host"],
        "port": fiware_environment["mqtt_port"],
        "username": None,  # Anonymous access configured
        "password": None,
        "topic_prefix": "encodapy/test",
    }


@pytest.fixture
def mqtt_connection(mqtt_environment):
    """
    Fixture providing a configured MqttConnection instance for integration tests.

    Args:
        mqtt_environment: The MQTT environment fixture (unused but required for Docker env)

    Returns:
        MqttConnection: Configured but not yet connected instance
    """

    connection = MqttConnection()
    connection.mqtt_params = MQTTEnvVariables(
        host=mqtt_environment["host"],
        port=mqtt_environment["port"],
        topic_prefix=mqtt_environment["topic_prefix"],
        username=mqtt_environment.get("username"),
        password=mqtt_environment.get("password"),
        tls_enabled=False,
        skip_none_values=False,
        publish_delay=0.0,
        timestamp_key="TimeInstant",
    )
    return connection


@pytest.fixture
def mqtt_connection_connected(mqtt_connection):
    """
    Fixture providing a connected MqttConnection instance.

    Args:
        mqtt_connection: The configured MQTT connection fixture

    Yields:
        MqttConnection: Connected instance with message store initialized

    Note:
        The connection is properly closed after the test
    """
    # Create a minimal mock config for message store preparation
    # We only need inputs and outputs for prepare_mqtt_message_store
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
                AttributeModel(
                    id="humidity",
                    id_interface="humidity",
                    type=AttributeTypes.VALUE,
                    value=None,
                ),
                AttributeModel(
                    id="command",
                    id_interface="cmdexe",
                    type=AttributeTypes.VALUE,
                    value=None,
                ),
            ],
        ),
    ]
    mock_config.outputs = []

    mqtt_connection.config = mock_config

    # Prepare the connection
    mqtt_connection.prepare_mqtt_connection()

    # Wait for connection to be established
    if not mqtt_connection._mqtt_connection_event.wait(timeout=10):
        raise TimeoutError(
            "MQTT connection not established within 10 seconds. "
            "Check if Mosquitto broker is running."
        )

    # Wait for subscriptions to be established
    # This ensures that published messages are received
    time.sleep(1)

    yield mqtt_connection

    # Clean up
    mqtt_connection.stop_mqtt_client()


@pytest.fixture
def mqtt_test_topics():
    """Fixture providing test topic names."""
    return {
        "entity": "encodapy/test/TestEntity:001",
        "temperature": "encodapy/test/TestEntity:001/temperature",
        "humidity": "encodapy/test/TestEntity:001/humidity",
        "command": "encodapy/test/TestEntity:001/cmdexe",
    }
