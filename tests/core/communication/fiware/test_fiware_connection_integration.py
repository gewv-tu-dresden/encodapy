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
- Time calculation utilities for different query methods

NOT the FILIP library itself (FILIP tests are in tests/docker/test_fiware.py).

Test Strategy:
- Integration tests using testcontainers for Docker management
- Real network calls to FIWARE services in containers
- Focus on end-to-end scenarios

Requires:
- Docker containers running (via testcontainers)
- testcontainers package installed
- pyyaml for example config loading
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
from filip.clients.exceptions import BaseHttpClientException
from filip.models.base import DataType
from filip.models.ngsi_v2.context import ContextEntity, NamedContextAttribute, ContextAttribute
from filip.models.ngsi_v2.base import NamedMetadata

from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    ConfigModel,
    DataQueryTypes,
    InputModel,
    InterfaceModel,
    Interfaces,
    OutputModel,
    TimerangeTypes
)
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.models import (
    DatabaseParameter,
    FiwareConnectionParameter,
    FiwareParameter,
    InputDataAttributeModel,
    MetaDataModel,
    OutputDataEntityModel,
    InputDataEntityModel
)
from encodapy.config import (
    ControllerSettingModel,
    TimeSettingsModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsResultsModel,
)
from encodapy.utils.units import DataUnits, TimeUnits
from encodapy.utils.cratedb import CrateDBConnection

# ============================================================================
# Test Fixtures
# ============================================================================
from tests.docker.conftest import fiware_cb_client

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]

# ============================================================================
# Fixtures: Connection Parameter und Clients
# ============================================================================
@pytest.fixture
def fiware_conn_params(fiware_envs) -> FiwareConnectionParameter:
    """Create a fully configured FiwareConnectionParameter object from Docker environment.
    
    Uses the real FIWARE service URLs from the Docker fixtures to create
    connection parameters for testing against the actual Docker containers.
    
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
    
    Creates a real CrateDBConnection instance connected to the CrateDB
    container running in Docker.
    
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
    """Example input entity based on 04_simple_service_fiware."""
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
    """Example output entity based on 04_simple_service_fiware."""
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

# ============================================================================
# Helper Functions
# ============================================================================
def create_mock_config() -> ConfigModel:
    """Creates a minimal ConfigModel instance for testing."""
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

def create_fiware_entity_from_model(
    fiware_cb_client: ContextBrokerClient,
    entity_model: InputModel | OutputModel,
    entity_type: str = "TestEntity"
) -> ContextEntity:
    """Creates a FIWARE entity based on an EnCoDaPy input/output model."""
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

# ============================================================================
# Test Classes
# ============================================================================

class TestFiwareConnectionSetup:
    """Tests for FiwareConnection setup and configuration."""

    def test_prepare_fiware_connection(self, fiware_conn_params):
        """Test that prepare_fiware_connection() sets up clients correctly."""
        conn = FiwareConnection()
        conn.fiware_conn_params = fiware_conn_params
        conn.prepare_fiware_connection()

        assert conn.cb_client is not None
        assert conn.crate_db_client is not None
        assert isinstance(conn.cb_client, ContextBrokerClient)

    def test_load_fiware_params_from_env(self, fiware_envs, monkeypatch):
        """Test load_fiware_params() with real environment variables from Docker."""
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
        """Test check_fiware_connection() when entities exist."""
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
    """Tests for data retrieval from FIWARE."""

    def test_get_metadata_from_fiware(self):
        """Test _get_metadata_from_fiware() method."""
        timestamp = datetime(2024, 1, 15, 12, 0, 0,
                             tzinfo=timezone.utc
                             ).strftime("%Y-%m-%dT%H:%M:%SZ")
        fiware_attribute = NamedContextAttribute(
            name="temperature",
            value=100.0,
            type=DataType.NUMBER,
            metadata=[
                NamedMetadata(
                    name="TimeInstant",
                    type=DataType.DATETIME,
                    value=timestamp,
                ),
                NamedMetadata(
                    name="unitCode",
                    type=DataType.TEXT,
                    value="CEL",
                ),
            ],
        )

        conn = FiwareConnection()
        metadata = conn._get_metadata_from_fiware(fiware_attribute)

        assert isinstance(metadata, MetaDataModel)
        assert metadata.timestamp is not None
        assert metadata.timestamp == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        assert metadata.unit == DataUnits.DEGREECELSIUS

    def test_get_metadata_from_fiware_no_timestamp(self):
        """Test _get_metadata_from_fiware() with no timestamp."""
        fiware_attribute = ContextAttribute(
            name="temperature",
            value=100.0,
            type=DataType.NUMBER,
            metadata=[],
        )

        conn = FiwareConnection()
        metadata = conn._get_metadata_from_fiware(fiware_attribute)

        assert isinstance(metadata, MetaDataModel)
        assert metadata.timestamp is None
        assert metadata.unit is None

    def test_get_data_from_fiware(self, fiware_cb_client, example_input_entity, fiware_conn_params):
        """Test get_data_from_fiware() with example input entity."""
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
        """Test _get_last_timestamp_for_fiware_output() with example output entity."""
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
    """Tests for data sending to FIWARE."""

    def test_adjust_units_for_fiware(self):
        """Test _adjust_units_for_fiware() method."""
        conn = FiwareConnection()

        attribute = AttributeModel(
            id="test_attr",
            value=100.0,
            unit=DataUnits.WTT,
            datatype=DataType.NUMBER,
        )

        result_attr, metadata = conn._adjust_units_for_fiware(
            id_output_entity="test_entity",
            attribute=attribute,
            fiware_unit=DataUnits.WTT,
        )

        assert result_attr.value == 100.0
        assert result_attr.unit == DataUnits.WTT
        assert len(metadata) > 0
        assert any(m.name == "unitCode" for m in metadata)

    def test_adjust_units_for_fiware_conversion(self):
        """Test _adjust_units_for_fiware() with unit conversion."""
        conn = FiwareConnection()

        attribute = AttributeModel(
            id="test_attr",
            value=1000.0,
            unit=DataUnits.WTT,
            datatype=DataType.NUMBER,
        )

        result_attr, metadata = conn._adjust_units_for_fiware(
            id_output_entity="test_entity",
            attribute=attribute,
            fiware_unit=DataUnits.KWT,
        )

        assert result_attr.value == 1.0  # 1000W = 1kW
        assert result_attr.unit == DataUnits.KWT
        assert len(metadata) > 0

    def test_adjust_units_for_fiware_no_unit(self):
        """Test _adjust_units_for_fiware() with no EnCoDaPy unit."""
        conn = FiwareConnection()

        attribute = AttributeModel(
            id="test_attr",
            value=100.0,
            unit=None,
            datatype=DataType.NUMBER,
        )

        result_attr, metadata = conn._adjust_units_for_fiware(
            id_output_entity="test_entity",
            attribute=attribute,
            fiware_unit=DataUnits.WTT,
        )

        assert result_attr.value == 100.0
        assert result_attr.unit is None
        assert len(metadata) == 1
        assert metadata[0].name == "unitCode"
        assert metadata[0].value == DataUnits.WTT.value

    def test_adjust_units_for_fiware_no_fiware_unit(self):
        """Test _adjust_units_for_fiware() with no FIWARE unit."""
        conn = FiwareConnection()

        attribute = AttributeModel(
            id="test_attr",
            value=100.0,
            unit=DataUnits.WTT,
            datatype=DataType.NUMBER,
        )

        result_attr, metadata = conn._adjust_units_for_fiware(
            id_output_entity="test_entity",
            attribute=attribute,
            fiware_unit=None,
        )

        assert result_attr.value == 100.0
        assert result_attr.unit == DataUnits.WTT
        assert len(metadata) > 0

    @pytest.mark.asyncio
    async def test_send_data_to_fiware(
        self,
        fiware_cb_client,
        example_output_entity,
        fiware_conn_params
    ):
        """Test _send_data_to_fiware() with example output entity."""
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
    """Tests for CrateDB data retrieval."""

    def test_get_data_from_database(
        self,
        fiware_cb_client,
        cratedb_client,
        example_output_entity,
        fiware_conn_params,
        fiware_envs
    ):
        """Test get_data_from_datebase() with example output entity."""
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

        # Prepare entity_attributes dict as expected by get_data_from_datebase
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
            pass

class TestFiwareConnectionTimeCalculation:
    """Tests for time calculation methods."""

    def test_calculate_timerange_absolute(self):
        """Test _calculate_timerange() with absolute timerange."""
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = None

        from_date, to_date = conn._calculate_timerange(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_value=3600,
            timerange_type=TimerangeTypes.ABSOLUTE,
        )

        assert from_date is not None
        assert to_date is None
        expected_from = (time_now - timedelta(seconds=3600)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert from_date == expected_from

    def test_calculate_timerange_relative(self):
        """Test _calculate_timerange() with relative timerange."""
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        from_date, to_date = conn._calculate_timerange(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_value=7200,
            timerange_type=TimerangeTypes.RELATIVE,
        )

        assert from_date is not None
        assert to_date is not None
        expected_from = last_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        expected_to = (last_timestamp + timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert from_date == expected_from
        assert to_date == expected_to

    def test_calculate_timerange_min_max(self):
        """Test _calculate_timerange_min_max() method."""
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        from_date, to_date = conn._calculate_timerange_min_max(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_min=1800,
            timerange_max=3600,
        )

        assert from_date is not None
        assert to_date is not None

    def test_calculate_dates_calculation(self):
        """Test _calculate_dates() with CALCULATION method."""
        conn = FiwareConnection()
        conn.config = create_mock_config()

        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from_date, to_date = conn._calculate_dates(
            method=DataQueryTypes.CALCULATION,
            last_timestamp=last_timestamp,
        )

        assert from_date is not None
        assert to_date is not None

    def test_calculate_dates_calibration(self):
        """Test _calculate_dates() with CALIBRATION method."""
        conn = FiwareConnection()
        conn.config = create_mock_config()

        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from_date, to_date = conn._calculate_dates(
            method=DataQueryTypes.CALIBRATION,
            last_timestamp=last_timestamp,
        )

        assert from_date is not None
        assert to_date is not None
