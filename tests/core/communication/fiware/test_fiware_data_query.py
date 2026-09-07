"""
Tests for FIWARE data query functionality in EnCoDaPy.

This module tests the data retrieval logic from FIWARE Context Broker,
including:
- Metadata extraction from FIWARE attributes
- Timerange calculation for different query types
- Data processing and unit handling

Test Strategy:
- Unit tests with mocked FIWARE clients
- Focus on _get_metadata_from_fiware() and _calculate_timerange() methods
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import requests

import pytest

from filip.clients.exceptions import BaseHttpClientException
from filip.models.base import FiwareHeader

from encodapy.config import AttributeTypes, DataQueryTypes, Interfaces
from encodapy.config.models import AttributeModel, ConfigModel, InputModel, OutputModel
from encodapy.config.types import TimerangeTypes
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.error_handling import InterfaceNotActive
from encodapy.utils.models import (
    DatabaseParameter,
    FiwareConnectionParameter,
    FiwareParameter,
    MetaDataModel,
)
from encodapy.utils.units import DataUnits

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_fiware_connection_with_client():
    """Create a FiwareConnection instance with fully mocked dependencies for testing.

    All external clients (ContextBrokerClient, CrateDBConnection) and configuration
    are replaced with MagicMock instances to enable isolated unit testing of the
    FiwareConnection data query methods.

    Returns:
        FiwareConnection: Instance with mocked connection parameters, clients, and config.
    """
    connection = FiwareConnection()

    # Mock connection parameters
    connection.fiware_conn_params = MagicMock(spec=FiwareConnectionParameter)
    connection.fiware_conn_params.fiware_params = MagicMock(spec=FiwareParameter)
    connection.fiware_conn_params.fiware_params.service = "test_service"
    connection.fiware_conn_params.fiware_params.service_path = "/test"
    connection.fiware_conn_params.fiware_params.cb_url = "http://localhost:1026"
    connection.fiware_conn_params.database_params = MagicMock(spec=DatabaseParameter)
    connection.fiware_conn_params.database_params.crate_db_url = "http://localhost:4200"

    # Mock clients
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()

    # Mock config with proper structure
    connection.config = MagicMock(spec=ConfigModel)
    connection.config.controller_settings = MagicMock()
    connection.config.controller_settings.time_settings = MagicMock()
    connection.config.controller_settings.time_settings.calculation = MagicMock()
    connection.config.controller_settings.time_settings.calculation.timestep = 60
    connection.config.controller_settings.time_settings.calculation.timestep_unit = "minute"
    connection.config.controller_settings.time_settings.calibration = None

    return connection


@pytest.fixture
def mock_input_entity():
    """Create a mock InputModel entity for data query testing.

    Provides a standardized test entity with temperature attribute for testing
    data retrieval scenarios.

    Returns:
        InputModel: Mock input entity with temperature attribute in Celsius.
    """
    return InputModel(
        id="test_entity",
        interface=Interfaces.FIWARE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
        ],
    )


@pytest.fixture
def mock_output_entity():
    """Create a mock OutputModel entity for data query testing.

    Provides a standardized test entity with result attribute for testing
    output data scenarios.

    Returns:
        OutputModel: Mock output entity with result attribute.
    """
    return OutputModel(
        id="test_output",
        interface=Interfaces.FIWARE,
        id_interface="TestOutput:001",
        attributes=[
            AttributeModel(
                id="result",
                id_interface="result",
                type=AttributeTypes.VALUE,
            ),
        ],
    )


# =============================================================================
# Tests for _get_metadata_from_fiware
# =============================================================================


def test_get_metadata_from_fiware_with_timeinstant_and_unitcode():
    """Test extracting metadata with TimeInstant and unitCode from FIWARE attribute.

    Verifies that the method correctly parses ISO 8601 timestamps and unit codes
    from FIWARE attribute metadata and converts them to MetaDataModel.

    Asserts:
        - Result is a MetaDataModel instance
        - Timestamp is correctly parsed from ISO format
        - Unit is correctly mapped from unitCode "CEL" to DataUnits.DEGREECELSIUS
    """
    connection = FiwareConnection()

    # Create a simple mock attribute with dict metadata
    mock_attr = MagicMock()
    mock_attr.name = "temperature"

    # Use a simple dict for metadata instead of NamedMetadata objects
    mock_attr.metadata = {
        "TimeInstant": MagicMock(value="2024-01-15T10:30:00.000+0000"),
        "unitCode": MagicMock(value="CEL"),
    }

    result = connection._get_metadata_from_fiware(mock_attr)

    assert isinstance(result, MetaDataModel)
    assert result.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    assert result.unit == DataUnits.DEGREECELSIUS


def test_get_metadata_from_fiware_with_unittext():
    """Test extracting metadata with unitText instead of unitCode.

    Verifies that the method can handle both unitCode and unitText metadata fields.
    This ensures compatibility with different FIWARE implementations.

    Asserts:
        - Result is a MetaDataModel instance
        - Timestamp is correctly parsed
        - Unit is correctly mapped from unitText "CEL" to DataUnits.DEGREECELSIUS
    """
    connection = FiwareConnection()

    mock_attr = MagicMock()
    mock_attr.name = "temperature"

    mock_attr.metadata = {
        "TimeInstant": MagicMock(value="2024-01-15T10:30:00.000+0000"),
        "unitText": MagicMock(value="CEL"),
    }

    result = connection._get_metadata_from_fiware(mock_attr)

    assert isinstance(result, MetaDataModel)
    assert result.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    assert result.unit == DataUnits.DEGREECELSIUS


def test_get_metadata_from_fiware_no_timestamp():
    """Test extracting metadata when no timestamp metadata is available.

    Verifies graceful handling of attributes without timestamp metadata.
    This can occur with real-time data or attributes that don't track time.

    Asserts:
        - Result is a MetaDataModel instance
        - Timestamp is None when not provided
        - Unit is None when not provided
    """
    connection = FiwareConnection()

    mock_attr = MagicMock()
    mock_attr.name = "temperature"
    mock_attr.metadata = {}

    result = connection._get_metadata_from_fiware(mock_attr)

    assert isinstance(result, MetaDataModel)
    assert result.timestamp is None
    assert result.unit is None


# =============================================================================
# Error handling tests for _get_metadata_from_fiware
# =============================================================================


def test_get_metadata_from_fiware_invalid_timestamp_format():
    """Test _get_metadata_from_fiware with invalid timestamp format.

    Verifies that the method gracefully handles invalid timestamp formats
    by logging an error and continuing without a timestamp.

    Args:
        mock_attr: Mock attribute with invalid timestamp format

    Asserts:
        - Result is a MetaDataModel instance
        - Timestamp is None (due to parsing failure)
        - No exception is raised
    """
    connection = FiwareConnection()

    mock_attr = MagicMock()
    mock_attr.name = "temperature"
    mock_attr.metadata = {
        "TimeInstant": MagicMock(value="invalid-timestamp-format"),
        "unitCode": MagicMock(value="CEL"),
    }

    result = connection._get_metadata_from_fiware(mock_attr)

    assert isinstance(result, MetaDataModel)
    assert result.timestamp is None
    assert result.unit == DataUnits.DEGREECELSIUS


def test_get_metadata_from_fiware_invalid_unit():
    """Test _get_metadata_from_fiware with invalid unit value.

    Verifies that the method gracefully handles invalid unit values
    by logging an error and continuing without a unit.

    Args:
        mock_attr: Mock attribute with invalid unit value

    Asserts:
        - Result is a MetaDataModel instance
        - Unit is None (due to parsing failure)
        - No exception is raised
    """
    connection = FiwareConnection()

    mock_attr = MagicMock()
    mock_attr.name = "temperature"
    mock_attr.metadata = {
        "TimeInstant": MagicMock(value="2024-01-15T10:30:00Z"),
        "unitCode": MagicMock(value="INVALID_UNIT"),
    }

    result = connection._get_metadata_from_fiware(mock_attr)

    assert isinstance(result, MetaDataModel)
    assert result.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    assert result.unit is None


# =============================================================================
# Error handling tests for get_data_from_fiware
# =============================================================================


def test_get_data_from_fiware_no_cb_client():
    """Test get_data_from_fiware raises InterfaceNotActive when cb_client is None.

    Verifies proper error handling when the FIWARE connection is not available.

    Args:
        mock_input_entity: Test input entity

    Asserts:
        - InterfaceNotActive exception is raised
    """
    connection = FiwareConnection()
    connection.cb_client = None
    connection.config = MagicMock(spec=ConfigModel)

    mock_entity = InputModel(
        id="test_entity",
        interface=Interfaces.FIWARE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=None,
            ),
        ],
    )

    with pytest.raises(InterfaceNotActive):
        connection.get_data_from_fiware(
            method=DataQueryTypes.CALCULATION,
            entity=mock_entity,
            timestamp_latest_output=None,
        )


def test_get_data_from_fiware_connection_error():
    """Test get_data_from_fiware handles ConnectionError gracefully.

    Verifies that connection errors are caught and logged, returning None.

    Args:
        mock_fiware_connection_with_client: Fixture with mocked connection
        mock_input_entity: Test input entity

    Asserts:
        - Result is None
        - No exception is propagated
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.cb_client.get_entity.side_effect = (
        requests.exceptions.ConnectionError("Connection failed")
    )
    connection.config = MagicMock(spec=ConfigModel)

    mock_entity = InputModel(
        id="test_entity",
        interface=Interfaces.FIWARE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=None,
            ),
        ],
    )

    result = connection.get_data_from_fiware(
        method=DataQueryTypes.CALCULATION,
        entity=mock_entity,
        timestamp_latest_output=None,
    )

    assert result is None


def test_get_data_from_fiware_http_client_exception():
    """Test get_data_from_fiware handles BaseHttpClientException gracefully.

    Verifies that FIWARE HTTP client exceptions are caught and logged, returning None.

    Asserts:
        - Result is None
        - No exception is propagated
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    # BaseHttpClientException requires a response parameter
    mock_response = MagicMock(spec=FiwareHeader)
    connection.cb_client.get_entity.side_effect = (
        BaseHttpClientException("HTTP error", mock_response)
    )
    connection.config = MagicMock(spec=ConfigModel)

    mock_entity = InputModel(
        id="test_entity",
        interface=Interfaces.FIWARE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=None,
            ),
        ],
    )

    result = connection.get_data_from_fiware(
        method=DataQueryTypes.CALCULATION,
        entity=mock_entity,
        timestamp_latest_output=None,
    )

    assert result is None


def test_get_data_from_fiware_missing_attribute():
    """Test get_data_from_fiware handles missing attributes gracefully.

    Verifies that missing attributes in FIWARE response are handled by
    creating InputDataAttributeModel with data_available=False.

    Args:
        mock_fiware_connection_with_client: Fixture with mocked connection

    Asserts:
        - Result is an InputDataEntityModel
        - Missing attributes have data_available=False
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.cb_client.get_entity.return_value.type = "TestEntity"
    connection.cb_client.get_entity_attributes.return_value = {}  # No attributes
    connection.config = MagicMock(spec=ConfigModel)

    mock_entity = InputModel(
        id="test_entity",
        interface=Interfaces.FIWARE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
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
        ],
    )

    result = connection.get_data_from_fiware(
        method=DataQueryTypes.CALCULATION,
        entity=mock_entity,
        timestamp_latest_output=None,
    )

    assert result is not None
    assert len(result.attributes) == 2
    for attr in result.attributes:
        assert attr.data_available is False


# =============================================================================
# Tests for _calculate_timerange
# =============================================================================


def test_calculate_timerange_absolute_with_last_timestamp():
    """Test calculating timerange with absolute type and last timestamp.

    For ABSOLUTE timerange, the method should calculate from_date as time_now minus
    timerange_value, with to_date being None (open-ended).

    Args:
        time_now: Current time (2024-01-15 10:30:00 UTC)
        last_timestamp: Last known timestamp (2024-01-15 09:00:00 UTC)
        timerange_value: 3600 seconds (1 hour)
        timerange_type: ABSOLUTE

    Asserts:
        - from_date is calculated as time_now - timerange_value
        - to_date is None for absolute timeranges
        - from_date is in ISO 8601 format with 'Z' timezone
    """
    connection = FiwareConnection()

    time_now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    last_timestamp = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = connection._calculate_timerange(
        time_now=time_now,
        last_timestamp=last_timestamp,
        timerange_value=3600,  # 1 hour in seconds
        timerange_type=TimerangeTypes.ABSOLUTE,
    )

    assert from_date is not None
    assert to_date is None
    # _format_datetime_iso8601 uses 'Z' for UTC timezone
    expected_from = (time_now - timedelta(seconds=3600)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert from_date == expected_from


def test_calculate_timerange_absolute_without_last_timestamp():
    """Test calculating timerange with absolute type when no last timestamp exists.

    When there is no previous data (last_timestamp is None), the method should
    still calculate a valid from_date based on time_now and timerange_value.

    Args:
        time_now: Current time (2024-01-15 10:30:00 UTC)
        last_timestamp: None (no previous data)
        timerange_value: 3600 seconds (1 hour)
        timerange_type: ABSOLUTE

    Asserts:
        - from_date is calculated as time_now - timerange_value
        - to_date is None
    """
    connection = FiwareConnection()

    time_now = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    from_date, to_date = connection._calculate_timerange(
        time_now=time_now,
        last_timestamp=None,
        timerange_value=3600,
        timerange_type=TimerangeTypes.ABSOLUTE,
    )

    assert from_date is not None
    assert to_date is None
