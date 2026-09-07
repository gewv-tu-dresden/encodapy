"""
Integration tests for FIWARE communication in EnCoDaPy.

This module contains integration tests for the FIWARE communication layer,
testing real interactions with FIWARE services running in Docker containers.

Tests cover:
- End-to-end FIWARE connection scenarios
- Data retrieval and submission
- CrateDB time-series operations
- Configuration integration

Requires:
- Docker containers running (via testcontainers)
- testcontainers package installed
"""

# pylint: disable=unused-import
from tests.core.communication.fiware.integration.conftest import (  # noqa: F401
    fiware_conn_params,
    cratedb_client,
    example_input_entity,
    example_output_entity,
    create_fiware_entity_from_model,
)
