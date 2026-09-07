"""
Test the FIWARE Docker environment and FILIP library functionality.

These tests verify that:
1. The Docker containers are running correctly
2. The FILIP library can interact with the FIWARE services

These are INFRASTRUCTURE tests, not EnCoDaPy-specific tests.
"""

import pytest
import requests
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.ngsi_v2.context import ContextEntity

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]


# ============================================================================
# Docker Environment Tests
# ============================================================================
@pytest.mark.order(1)
def test_orion_connection(fiware_environment):
    """
    Test the connection to the Orion Context Broker in the FIWARE Docker environment.
    """
    response = requests.get(f"{fiware_environment['orion']}/version", timeout=5)

    assert response.status_code == 200
    assert "orion" in response.json()

@pytest.mark.order(2)
def test_cratedb_connection(fiware_environment):
    """
    Test the connection to the CrateDB in the FIWARE Docker environment.
    """
    response = requests.get(f"{fiware_environment['cratedb']}/", timeout=5)

    assert response.status_code == 200
    assert "cluster_name" in response.json()


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_entity(cb_client: ContextBrokerClient, entity_id: str, entity_type: str,
                      attributes: list) -> ContextEntity:
    """
    Helper function to create a test entity in FIWARE.
    
    Args:
        cb_client: ContextBrokerClient instance
        entity_id: ID of the entity to create
        entity_type: Type of the entity
        attributes: List of NamedContextAttribute to add to the entity
        
    Returns:
        The created ContextEntity
    """
    entity = ContextEntity(id=entity_id, type=entity_type)
    cb_client.create_entity(entity)

    if attributes:
        cb_client.update_or_append_entity_attributes(
            entity_id=entity_id,
            entity_type=entity_type,
            attrs=attributes,
        )

    return entity
