"""
Integration test fixtures for FIWARE Docker-based testing.

This module provides fixtures for integration tests that require real FIWARE
services running in Docker containers. It re-exports fixtures from the docker
conftest and adds integration-specific fixtures.

Requires:
- Docker containers running (via testcontainers)
- testcontainers package installed
"""

# pylint: disable=redefined-outer-name, unused-import, broad-exception-caught
from datetime import datetime, timezone
import time

import pytest
from loguru import logger

from filip.clients.exceptions import BaseHttpClientException
from filip.models.base import DataType
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import ContextEntity, NamedContextAttribute
from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    InputModel,
    Interfaces,
    OutputModel,
)
from encodapy.utils.models import (
    DatabaseParameter,
    FiwareConnectionParameter,
    FiwareParameter,
)
from encodapy.utils.cratedb import CrateDBConnection
from encodapy.utils.units import DataUnits
from tests.docker.conftest import (  # noqa: F401
    fiware_environment,
    fiware_cb_client,
    fiware_envs,
    test_entity,
)


pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]


@pytest.fixture
def fiware_conn_params(fiware_envs) -> FiwareConnectionParameter:
    """Create a fully configured FiwareConnectionParameter object from Docker environment.

    Args:
        fiware_envs: Fixture providing FIWARE service URLs from Docker

    Returns:
        FiwareConnectionParameter: Configured connection parameters with FIWARE
            Context Broker URL, service info, and CrateDB connection parameters.
    """
    return FiwareConnectionParameter(
        fiware_params=FiwareParameter(
            cb_url=fiware_envs["cb_url"].rstrip('/'),
            service=fiware_envs["fiware_service"],
            service_path=fiware_envs["fiware_service_path"],
            authentication=None,
        ),
        database_params=DatabaseParameter(
            crate_db_url=fiware_envs["crate_db_url"].rstrip('/'),
            crate_db_user=fiware_envs["crate_db_user"],
            crate_db_pw=fiware_envs["crate_db_pw"],
            crate_db_ssl=fiware_envs["crate_db_ssl"],
        ),
    )


@pytest.fixture
def cratedb_client(fiware_envs) -> CrateDBConnection:
    """Create a CrateDB client for testing against Docker container.

    Args:
        fiware_envs: Fixture providing FIWARE service URLs from Docker

    Returns:
        CrateDBConnection: Real client connected to Docker CrateDB instance.
    """
    return CrateDBConnection(
        crate_db_url=fiware_envs["crate_db_url"].rstrip('/'),
        crate_db_user=fiware_envs["crate_db_user"],
        crate_db_pw=fiware_envs["crate_db_pw"],
        crate_db_ssl=fiware_envs["crate_db_ssl"],
    )


@pytest.fixture
def example_input_entity() -> InputModel:
    """Example input entity based on 04_simple_service_fiware for integration testing.

    Returns:
        InputModel: Test input entity with temperature attribute.
    """
    return InputModel(
        id="input_temperature",
        id_interface="urn:example:input:temperature",
        interface=Interfaces.FIWARE,
        attributes=[
            AttributeModel(
                id="temperature_input",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER,
                unit=DataUnits.DEGREECELSIUS,
            )
        ],
    )


@pytest.fixture
def example_output_entity() -> OutputModel:
    """Example output entity based on 04_simple_service_fiware for integration testing.

    Returns:
        OutputModel: Test output entity with temperature attribute.
    """
    return OutputModel(
        id="output_temperature",
        id_interface="urn:example:output:temperature",
        interface=Interfaces.FIWARE,
        attributes=[
            AttributeModel(
                id="temperature_output",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER,
                unit=DataUnits.DEGREECELSIUS,
            )
        ],
        commands=[],
    )


# Helper function for integration tests
def create_fiware_entity_from_model(
    fiware_cb_client,
    entity_model,
    entity_type: str = "TestEntity"
) -> "ContextEntity":
    """Create a FIWARE entity based on an EnCoDaPy input/output model.

    Args:
        fiware_cb_client: ContextBrokerClient instance
        entity_model: InputModel or OutputModel to create entity from
        entity_type: Type of the entity (default: "TestEntity")

    Returns:
        ContextEntity: Created FIWARE entity
    """
    entity_id = entity_model.id_interface

    # Try to delete the entity first to avoid conflicts
    try:
        fiware_cb_client.delete_entity(entity_id, entity_type)
    except Exception:
        pass

    # Wait a moment to ensure deletion is processed
    time.sleep(0.2)

    # Create the entity - use post_entity which should work for new entities
    entity = ContextEntity(id=entity_id, type=entity_type)
    try:
        fiware_cb_client.post_entity(entity, update=True)
    except Exception:
        # If create fails, try update
        try:
            fiware_cb_client.update_entity(entity)
        except BaseHttpClientException:
            pass

    # Wait a moment to ensure entity is created
    time.sleep(0.2)

    attrs = []
    for attr in entity_model.attributes:
        test_value = 25.5 if attr.datatype == DataType.NUMBER else "test"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        metadata_list = [
            NamedMetadata(
                name="TimeInstant",
                type=DataType.DATETIME,
                value=timestamp,
            )
        ]

        if attr.unit:
            metadata_list.append(
                NamedMetadata(
                    name="unitCode",
                    type=DataType.TEXT,
                    value=attr.unit.value,
                )
            )

        attrs.append(
            NamedContextAttribute(
                name=attr.id_interface,
                value=test_value,
                type=attr.datatype,
                metadata=metadata_list,
            )
        )

    try:
        fiware_cb_client.update_or_append_entity_attributes(
            entity_id=entity_id,
            entity_type=entity_type,
            attrs=attrs,
        )
    except BaseHttpClientException as e:
        logger.error(f"Failed to update attributes for entity {entity_id}: {e}")
        raise

    return entity
