"""
Unit tests for FIWARE timeseries data handling in EnCoDaPy.

This module tests the timeseries data preparation and sending functionality,
including:
- prepare_timeseries_for_fiware() method
- _send_timeseries_to_fiware() method
- DataFrame handling and validation
- Async timeseries operations

Test Strategy:
- Unit tests with mocked dependencies
- Focus on data validation, transformation, and error handling
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name
from unittest.mock import MagicMock

import pandas as pd
import pytest

from filip.models.base import DataType
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import ContextEntity, NamedContextAttribute

from encodapy.config import AttributeModel, AttributeTypes, OutputModel
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.models import FiwareDatapointParameter
from encodapy.utils.units import DataUnits


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_fiware_connection_timeseries():
    """Create a FiwareConnection instance configured for timeseries testing.

    Returns:
        FiwareConnection: Instance with mocked clients for timeseries operations.
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()
    return connection


@pytest.fixture
def mock_output_entity_timeseries():
    """Create a mock OutputModel with timeseries attribute for testing.

    Returns:
        OutputModel: Entity with timeseries temperature data.
    """
    return OutputModel(
        id="test_output_ts",
        interface="fiware",
        id_interface="TestOutputTS:001",
        attributes=[
            AttributeModel(
                id="temperature_ts",
                id_interface="temperature",
                type=AttributeTypes.TIMESERIES,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
        ],
    )


@pytest.fixture
def mock_fiware_datapoint():
    """Create a mock FiwareDatapointParameter with DataFrame for testing.

    Returns:
        FiwareDatapointParameter: Parameter with timeseries data.
    """
    df = pd.DataFrame({
        "temperature_ts": [20.0, 21.0, 22.0],
    }, index=pd.date_range("2024-01-15 10:00:00", periods=3, freq="10min"))

    entity = ContextEntity(id="TestOutputTS:001", type="TestOutputTS")
    attribute = AttributeModel(
        id="temperature_ts",
        id_interface="temperature",
        type=AttributeTypes.TIMESERIES,
        value=df,
        unit=DataUnits.DEGREECELSIUS,
    )

    return FiwareDatapointParameter(
        entity=entity,
        attribute=attribute,
        metadata=[],
    )


# =============================================================================
# Tests for prepare_timeseries_for_fiware
# =============================================================================


@pytest.mark.asyncio
async def test_prepare_timeseries_for_fiware_valid_dataframe():
    """Test prepare_timeseries_for_fiware with valid DataFrame input.

    Verifies that a valid DataFrame with timeseries data is correctly
    converted to NamedContextAttribute objects for FIWARE.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection
        mock_fiware_datapoint: Fixture with valid DataFrame

    Asserts:
        - Result is a NamedContextAttribute
        - Value is the last value from the DataFrame
        - Metadata contains TimeInstant
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    df = pd.DataFrame({
        "temperature_ts": [20.0, 21.0, 22.0],
    }, index=pd.date_range("2024-01-15 10:00:00", periods=3, freq="10min"))

    entity = ContextEntity(id="TestOutputTS:001", type="TestOutputTS")
    attribute = AttributeModel(
        id="temperature_ts",
        id_interface="temperature",
        type=AttributeTypes.TIMESERIES,
        value=df,
        unit=DataUnits.DEGREECELSIUS,
    )

    datapoint = FiwareDatapointParameter(
        entity=entity,
        attribute=attribute,
        metadata=[],
    )

    result = await connection.prepare_timeseries_for_fiware(
        fiware_datapoint=datapoint,
        datatype=DataType.NUMBER,
    )

    assert result is not None
    assert isinstance(result, NamedContextAttribute)
    assert result.name == "temperature"
    assert result.value == 22.0
    assert result.type == DataType.NUMBER
    # The method returns the last attribute with TimeInstant metadata
    assert hasattr(result, 'metadata')
    assert len(result.metadata) > 0


@pytest.mark.asyncio
async def test_prepare_timeseries_for_fiware_empty_dataframe():
    """Test prepare_timeseries_for_fiware with empty DataFrame.

    Verifies that an empty DataFrame returns an empty list.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection

    Asserts:
        - Result is an empty list
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    df = pd.DataFrame(columns=["temperature_ts"])

    entity = ContextEntity(id="TestOutputTS:001", type="TestOutputTS")
    attribute = AttributeModel(
        id="temperature_ts",
        id_interface="temperature",
        type=AttributeTypes.TIMESERIES,
        value=df,
        unit=DataUnits.DEGREECELSIUS,
    )

    datapoint = FiwareDatapointParameter(
        entity=entity,
        attribute=attribute,
        metadata=[],
    )

    result = await connection.prepare_timeseries_for_fiware(
        fiware_datapoint=datapoint,
        datatype=DataType.NUMBER,
    )

    assert result == []


@pytest.mark.asyncio
async def test_prepare_timeseries_for_fiware_missing_column():
    """Test prepare_timeseries_for_fiware when attribute ID is not in DataFrame columns.

    Verifies that missing columns are handled gracefully by returning empty list.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection

    Asserts:
        - Result is an empty list
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    df = pd.DataFrame({
        "wrong_column": [20.0, 21.0, 22.0],
    })

    entity = ContextEntity(id="TestOutputTS:001", type="TestOutputTS")
    attribute = AttributeModel(
        id="temperature_ts",  # This column doesn't exist in the DataFrame
        id_interface="temperature",
        type=AttributeTypes.TIMESERIES,
        value=df,
        unit=DataUnits.DEGREECELSIUS,
    )

    datapoint = FiwareDatapointParameter(
        entity=entity,
        attribute=attribute,
        metadata=[],
    )

    result = await connection.prepare_timeseries_for_fiware(
        fiware_datapoint=datapoint,
        datatype=DataType.NUMBER,
    )

    assert result == []


@pytest.mark.asyncio
async def test_prepare_timeseries_for_fiware_non_dataframe():
    """Test prepare_timeseries_for_fiware raises ValueError when value is not a DataFrame.

    Verifies that non-DataFrame values raise a ValueError with proper error message.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection

    Asserts:
        - ValueError is raised
        - Error message mentions invalid data type
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    entity = ContextEntity(id="TestOutputTS:001", type="TestOutputTS")
    attribute = AttributeModel(
        id="temperature_ts",
        id_interface="temperature",
        type=AttributeTypes.TIMESERIES,
        value=[20.0, 21.0, 22.0],  # List instead of DataFrame
        unit=DataUnits.DEGREECELSIUS,
    )

    datapoint = FiwareDatapointParameter(
        entity=entity,
        attribute=attribute,
        metadata=[],
    )

    with pytest.raises(ValueError, match="Invalid data type for FiwareDatapointParameter"):
        await connection.prepare_timeseries_for_fiware(
            fiware_datapoint=datapoint,
            datatype=DataType.NUMBER,
        )


# =============================================================================
# Tests for _send_timeseries_to_fiware
# =============================================================================


@pytest.mark.asyncio
async def test_send_timeseries_to_fiware_success():
    """Test _send_timeseries_to_fiware successfully sends timeseries data.

    Verifies that timeseries attributes are sent to FIWARE using the
    update_or_append_entity_attributes method.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection

    Asserts:
        - update_or_append_entity_attributes is called
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    attrs_timeseries = [
        NamedContextAttribute(
            name="temperature",
            value=20.0,
            type=DataType.NUMBER,
            metadata=[
                NamedMetadata(
                    name="TimeInstant", type=DataType.DATETIME, value="2024-01-15T10:00:00Z"
                )
            ],
        ),
        NamedContextAttribute(
            name="temperature",
            value=21.0,
            type=DataType.NUMBER,
            metadata=[
                NamedMetadata(
                    name="TimeInstant", type=DataType.DATETIME, value="2024-01-15T10:10:00Z"
                )
            ],
        ),
    ]

    await connection._send_timeseries_to_fiware(
        entity_id="TestOutputTS:001",
        entity_type="TestOutputTS",
        attrs_timeseries=attrs_timeseries,
    )

    # Verify that update_or_append_entity_attributes was called for each attribute
    assert (
        connection.cb_client.update_or_append_entity_attributes.call_count == len(attrs_timeseries)
    )


@pytest.mark.asyncio
async def test_send_timeseries_to_fiware_empty_list():
    """Test _send_timeseries_to_fiware with empty attributes list.

    Verifies that empty list is handled gracefully.

    Args:
        mock_fiware_connection_timeseries: Fixture with mocked connection

    Asserts:
        - No calls to update_or_append_entity_attributes
    """
    connection = FiwareConnection()
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()
    connection.config = MagicMock()

    await connection._send_timeseries_to_fiware(
        entity_id="TestOutputTS:001",
        entity_type="TestOutputTS",
        attrs_timeseries=[],
    )

    connection.cb_client.update_or_append_entity_attributes.assert_not_called()
