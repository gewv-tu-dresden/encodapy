# pylint: disable=redefined-outer-name
"""
Pytest for docker compose config

This module provides a fixture to start and stop the docker environment for integration tests.

"""
import time
import pytest
from testcontainers.compose import DockerCompose
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeader

@pytest.fixture(scope="session")
def fiware_environment():
    """
    Function starts the fiware docker stack via docker compose

    Yields:
        DockerCompose: An instance of the DockerCompose class representing \
            the running Docker Compose environment.
    """

    compose = DockerCompose(
        context="./tests/docker",
        compose_file_name="docker-compose.fiware.yml"
        )
    compose.start()

    # Wait for Containers
    time.sleep(20)

    yield {
        "orion": "http://127.0.0.1:1026",
        "cratedb": "http://127.0.0.1:4200",
        "mqtt_host": "127.0.0.1",
        "mqtt_port": 1883,
    }

    compose.stop()


@pytest.fixture
def fiware_cb_client(fiware_environment) -> ContextBrokerClient:
    """
    Fixture providing a real ContextBrokerClient connected to the Docker Orion instance.
    
    Args:
        fiware_environment: Fixture that provides the FIWARE service URLs
        
    Returns:
        ContextBrokerClient: Configured client for the test Orion instance.
    """
    return ContextBrokerClient(
        url=fiware_environment["orion"],
        fiware_header=FiwareHeader(
            service="test_service",
            service_path="/",
        ),
    )

@pytest.fixture
def fiware_envs(fiware_environment) -> dict:
    """Fixture providing FIWARE connection parameters for the Docker instance."""
    return {
        "cb_url": fiware_environment["orion"],
        "fiware_service": "test_service",
        "fiware_service_path": "/",
        "crate_db_url": fiware_environment["cratedb"],
        "crate_db_user": "crate",
        "crate_db_pw": "",
        "crate_db_ssl": False,
    }


@pytest.fixture
def test_entity() -> dict[str, str]:
    """Test entity ID and type used across tests."""
    return {
        "id": "urn:test:entity:integration",
        "type": "TestEntity"
    }
