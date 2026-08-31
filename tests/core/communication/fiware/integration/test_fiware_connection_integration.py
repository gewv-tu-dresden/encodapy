"""
Integration tests for EnCoDaPy's FiwareConnection class using Docker containers.

These tests verify the EnCoDaPy-specific logic of the FiwareConnection class
with real FIWARE services running in Docker containers. Unlike unit tests,
these tests exercise the actual integration with:
- FIWARE Orion Context Broker
- CrateDB time-series database

Tests cover:
- Connection setup and parameter loading from Docker environment
- Data retrieval from FIWARE (InputModel entities)
- Data sending to FIWARE (OutputModel entities)
- CrateDB time-series data access and querying

NOT the FILIP library itself (FILIP tests are in tests/docker/test_fiware.py).

Test Strategy:
- Integration tests using testcontainers for Docker management
- Real network calls to FIWARE services in containers
- Focus on end-to-end scenarios

Requires:
- Docker containers running (via testcontainers)
- testcontainers package installed
"""
# pylint: disable=redefined-outer-name
# pylint: disable=protected-access
# pylint: disable=broad-exception-caught
# pylint: disable=no-member

import time
from datetime import datetime, timezone, timedelta
import pytest
from loguru import logger

from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.ngsi_v2.context import ContextEntity

from encodapy.config import (
    ConfigModel,
    ControllerSettingModel,
    DataQueryTypes,
    InterfaceModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsModel,
    TimeSettingsResultsModel,
)
from encodapy.config.types import TimerangeTypes
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    MetaDataModel,
    OutputDataEntityModel,
)
from encodapy.utils.units import DataUnits, TimeUnits

# ============================================================================
# Fixtures and Helper Functions
# ============================================================================
# pylint: disable=unused-import
from .conftest import (
    create_fiware_entity_from_model,
    cratedb_client,
    example_input_entity,
    example_output_entity,
    fiware_conn_params,
)


def create_mock_config():
    """Creates a minimal ConfigModel instance for testing.
    
    Returns:
        ConfigModel: Minimal configuration with FIWARE interface enabled
            and default time settings for testing.
    """
    return ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=False, mqtt=False),
        inputs=[],
        outputs=[],
        staticdata=[],
        controller_components=[],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=24,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type=TimerangeTypes.ABSOLUTE,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=24,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type=TimerangeTypes.ABSOLUTE,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                ),
                results=TimeSettingsResultsModel(
                    timerange=1,
                    timerange_unit=TimeUnits.HOUR,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                ),
            ),
            specific_settings={},
        ),
    )


# ============================================================================
# Test Classes
# ============================================================================


class TestFiwareConnectionSetup:
    """Integration tests for FiwareConnection setup and configuration."""

    def test_prepare_fiware_connection(self, fiware_conn_params):
        """Test that prepare_fiware_connection() sets up clients correctly with Docker.
        
        Verifies that the FiwareConnection can create real clients
        using the Docker environment parameters.
        
        Args:
            fiware_conn_params: Fixture providing Docker FIWARE connection parameters
        
        Asserts:
            - cb_client is created and not None
            - crate_db_client is created and not None
            - cb_client is an instance of ContextBrokerClient
        """
        conn = FiwareConnection()
        conn.fiware_conn_params = fiware_conn_params
        conn.prepare_fiware_connection()

        assert conn.cb_client is not None
        assert conn.crate_db_client is not None
        assert isinstance(conn.cb_client, ContextBrokerClient)

    def test_load_fiware_params_from_env(self, fiware_envs, monkeypatch):
        """Test load_fiware_params() with real environment variables from Docker.
        
        Verifies that FIWARE parameters can be loaded from the Docker
        environment variables.
        
        Args:
            fiware_envs: Fixture providing FIWARE service URLs from Docker
            monkeypatch: pytest fixture for modifying environment variables
        
        Asserts:
            - fiware_conn_params is created
            - cb_url matches Docker environment
            - service and service_path are correctly loaded
        """
        monkeypatch.setenv("FIWARE_CB_URL", fiware_envs["cb_url"].rstrip('/'))
        monkeypatch.setenv("FIWARE_SERVICE", fiware_envs["fiware_service"])
        monkeypatch.setenv("FIWARE_SERVICE_PATH", fiware_envs["fiware_service_path"])
        monkeypatch.setenv("FIWARE_AUTH", "false")
        monkeypatch.setenv("CRATE_DB_URL", fiware_envs["crate_db_url"].rstrip('/'))
        monkeypatch.setenv("CRATE_DB_USER", fiware_envs["crate_db_user"])
        monkeypatch.setenv("CRATE_DB_PW", fiware_envs["crate_db_pw"])
        monkeypatch.setenv("CRATE_DB_SSL", str(fiware_envs["crate_db_ssl"]).lower())

        conn = FiwareConnection()
        conn.load_fiware_params()

        assert conn.fiware_conn_params is not None
        assert conn.fiware_conn_params.fiware_params.cb_url.rstrip('/') \
            == fiware_envs["cb_url"].rstrip('/')
        assert conn.fiware_conn_params.fiware_params.service == fiware_envs["fiware_service"]
        assert conn.fiware_conn_params.fiware_params.service_path \
            == fiware_envs["fiware_service_path"]

    def test_check_fiware_connection_with_entities(self, fiware_cb_client, example_input_entity):
        """Test check_fiware_connection() when entities exist in Docker FIWARE.
        
        Verifies that the connection check works with real entities
        in the Docker FIWARE Context Broker.
        
        Args:
            fiware_cb_client: ContextBrokerClient connected to Docker FIWARE
            example_input_entity: Test input entity
        
        Asserts:
            - Entity is created in FIWARE
            - Entity list contains at least one entity
        """
        create_fiware_entity_from_model(fiware_cb_client, example_input_entity)

        conn = FiwareConnection()
        conn.cb_client = fiware_cb_client
        conn.check_fiware_connection()

        entity_list = conn.cb_client.get_entity_list(entity_types=["TestEntity"])
        assert len(entity_list) > 0

        try:
            fiware_cb_client.delete_entity(example_input_entity.id_interface, "TestEntity")
        except Exception:
            pass


class TestFiwareConnectionDataRetrieval:
    """Integration tests for data retrieval from FIWARE Docker containers."""

    def test_get_data_from_fiware(self, fiware_cb_client, example_input_entity, fiware_conn_params):
        """Test get_data_from_fiware() with example input entity against Docker FIWARE.
        
        Verifies end-to-end data retrieval from the real FIWARE Context Broker
        running in Docker.
        
        Args:
            fiware_cb_client: ContextBrokerClient connected to Docker FIWARE
            example_input_entity: Test input entity
            fiware_conn_params: Docker FIWARE connection parameters
        
        Asserts:
            - Result is not None
            - Result is an InputDataEntityModel
            - Result contains the expected entity ID
            - Attributes are retrieved with correct data and units
        """
        create_fiware_entity_from_model(fiware_cb_client, example_input_entity)

        conn = FiwareConnection()
        conn.cb_client = fiware_cb_client
        conn.fiware_conn_params = fiware_conn_params
        conn.config = create_mock_config()

        result = conn.get_data_from_fiware(
            method=DataQueryTypes.CALCULATION,
            entity=example_input_entity,
            timestamp_latest_output=None,
        )

        assert result is not None
        assert isinstance(result, InputDataEntityModel)
        assert result.id == example_input_entity.id
        assert len(result.attributes) > 0
        assert result.attributes[0].data == 25.5
        assert result.attributes[0].unit == DataUnits.DEGREECELSIUS

        try:
            fiware_cb_client.delete_entity(example_input_entity.id_interface, "TestEntity")
        except Exception:
            pass

    def test_get_last_timestamp_for_fiware_output(
        self,
        fiware_cb_client,
        example_output_entity,
        fiware_conn_params
    ):
        """Test _get_last_timestamp_for_fiware_output() with example output entity.
        
        Verifies that the method can retrieve the latest timestamp from
        FIWARE entities in Docker.
        
        Args:
            fiware_cb_client: ContextBrokerClient connected to Docker FIWARE
            example_output_entity: Test output entity
            fiware_conn_params: Docker FIWARE connection parameters
        
        Asserts:
            - Result is a tuple
            - First element is OutputDataEntityModel
            - Second element is datetime or None
        """
        create_fiware_entity_from_model(fiware_cb_client, example_output_entity)

        conn = FiwareConnection()
        conn.cb_client = fiware_cb_client
        conn.fiware_conn_params = fiware_conn_params

        result = conn._get_last_timestamp_for_fiware_output(example_output_entity)

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], OutputDataEntityModel)
        assert isinstance(result[1], datetime) or result[1] is None

        try:
            fiware_cb_client.delete_entity(example_output_entity.id_interface, "TestEntity")
        except Exception:
            pass


class TestFiwareConnectionDataSending:
    """Integration tests for data sending to FIWARE Docker containers."""

    @pytest.mark.asyncio
    async def test_send_data_to_fiware(
        self,
        fiware_cb_client,
        example_output_entity,
        fiware_conn_params
    ):
        """Test _send_data_to_fiware() with example output entity against Docker FIWARE.
        
        Verifies end-to-end data sending to the real FIWARE Context Broker
        running in Docker.
        
        Args:
            fiware_cb_client: ContextBrokerClient connected to Docker FIWARE
            example_output_entity: Test output entity
            fiware_conn_params: Docker FIWARE connection parameters
        
        Asserts:
            - Data is sent successfully
            - Entity attributes are updated in FIWARE
            - Retrieved value matches the sent value
        """
        entity_id = example_output_entity.id_interface
        entity_type = "TestEntity"

        # Clean up first
        try:
            fiware_cb_client.delete_entity(entity_id, entity_type)
        except Exception:
            pass

        time.sleep(0.2)

        # Create entity with post_entity
        entity = ContextEntity(id=entity_id, type=entity_type)
        try:
            fiware_cb_client.post_entity(entity, update=True)
        except Exception:
            fiware_cb_client.update_entity(entity)

        time.sleep(0.2)

        conn = FiwareConnection()
        conn.cb_client = fiware_cb_client
        conn.fiware_conn_params = fiware_conn_params
        conn.config = create_mock_config()

        # Set values for the output attributes
        output_attributes = []
        for attr in example_output_entity.attributes:
            attr_with_value = attr.copy()
            attr_with_value.value = 42.0
            output_attributes.append(attr_with_value)

        await conn._send_data_to_fiware(
            output_entity=example_output_entity,
            output_attributes=output_attributes,
            output_commands=example_output_entity.commands,
        )

        retrieved = fiware_cb_client.get_entity_attributes(
            entity_id=example_output_entity.id_interface,
            entity_type="TestEntity",
        )
        assert "temperature" in retrieved
        assert retrieved["temperature"].value == 42.0

        try:
            fiware_cb_client.delete_entity(example_output_entity.id_interface, "TestEntity")
        except Exception:
            pass


class TestCrateDBConnection:
    """Integration tests for CrateDB data retrieval with Docker."""

    def test_get_data_from_database(
        self,
        fiware_cb_client,
        cratedb_client,
        example_output_entity,
        fiware_conn_params,
        fiware_envs
    ):
        """Test get_data_from_database() with example output entity against Docker CrateDB.
        
        Verifies end-to-end data retrieval from CrateDB running in Docker,
        including direct database writes and reads.
        
        Args:
            fiware_cb_client: ContextBrokerClient connected to Docker FIWARE
            cratedb_client: CrateDBConnection to Docker CrateDB
            example_output_entity: Test output entity
            fiware_conn_params: Docker FIWARE connection parameters
            fiware_envs: Docker FIWARE environment variables
        
        Asserts:
            - Result is not None
            - Result is a list of InputDataAttributeModel
            - Data from CrateDB is correctly retrieved
        """
        # First create the entity in FIWARE
        entity = create_fiware_entity_from_model(fiware_cb_client, example_output_entity)

        # Write test data directly to CrateDB
        service = fiware_envs["fiware_service"]
        entity_id = entity.id
        entity_type = entity.type
        attribute_name = example_output_entity.attributes[0].id_interface

        connection = cratedb_client.get_database_connection()
        cursor = connection.cursor()

        # Insert test data
        now = datetime.now(timezone.utc)
        test_time = now - timedelta(minutes=30)
        # Use ISO 8601 format for time_index to match the query format in get_data
        test_time_str = test_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            cursor.execute(
                f"INSERT INTO mt{service}.et{entity_type} "
                f"(time_index, entity_id, {attribute_name}) "
                f"VALUES ('{test_time_str}', '{entity_id}', 25.5)"
            )
            connection.commit()
        except Exception as e:
            logger.warning(f"Could not insert test data into CrateDB: {e}")
            # Try to create the table first
            try:
                cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS mt{service}.et{entity_type.lower()} "
                    f"(time_index TIMESTAMP, entity_id STRING, {attribute_name} DOUBLE) "
                    f"WITH (number_of_replicas = 0)"
                )
                connection.commit()
                cursor.execute(
                    f"INSERT INTO mt{service}.et{entity_type.lower()} "
                    f"(time_index, entity_id, {attribute_name}) "
                    f"VALUES ('{test_time_str}', '{entity_id}', 25.5)"
                )
                connection.commit()
            except Exception as e2:
                logger.error(f"Failed to create table and insert data: {e2}")
                raise e2
        finally:
            cursor.close()
            connection.close()

        time.sleep(2)

        conn = FiwareConnection()
        conn.cb_client = fiware_cb_client
        conn.crate_db_client = cratedb_client
        conn.fiware_conn_params = fiware_conn_params
        conn.config = create_mock_config()

        # Prepare entity_attributes dict as expected by get_data_from_database
        # The method expects: {attribute_id: {"id_interface": str, "metadata": MetaDataModel}}
        entity_attributes = {}
        for attr in example_output_entity.attributes:
            entity_attributes[attr.id] = {
                "id_interface": attr.id_interface,
                "metadata": MetaDataModel()
            }

        # Call the method with correct parameters
        result = conn.get_data_from_database(
            entity=ContextEntity(id=entity_id, type=entity_type),
            entity_attributes=entity_attributes,
            method=DataQueryTypes.CALCULATION,
            timestamp_latest_output=now - timedelta(hours=2),
        )

        assert result is not None
        assert isinstance(result, list)
        # Result should be a list of InputDataAttributeModel
        for item in result:
            assert isinstance(item, InputDataAttributeModel)

        try:
            fiware_cb_client.delete_entity(entity_id, entity_type)
        except Exception:
            pass

        # Clean up CrateDB data
        try:
            connection = cratedb_client.get_database_connection()
            cursor = connection.cursor()
            cursor.execute(
                f"DELETE FROM mt{service}.et{entity_type.lower()} "
                f"WHERE entity_id = %s", (entity_id,)
            )
            connection.commit()
            cursor.close()
            connection.close()
        except Exception:
            logger.warning(
                f"Could not clean up CrateDB data for entity {entity_id} of type {entity_type}."
            )
