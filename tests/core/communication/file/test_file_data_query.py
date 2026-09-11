"""
Tests for FILE data query functionality in EnCoDaPy.

This module tests the data retrieval logic from local files,
including:
- CSV file reading and data extraction
- JSON file reading and data extraction
- Data processing and time handling
- Error handling for file operations

Test Strategy:
- Unit tests with mocked file operations
- Focus on get_data_from_csv_file(), get_data_from_json_file() methods
- Tests for time parsing and data processing
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import os
import json
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from encodapy.config import AttributeTypes, DataQueryTypes, Interfaces
from encodapy.config.env_values import FileEnvVariables
from encodapy.config.models import AttributeModel, InputModel, StaticDataModel
from encodapy.service.communication.file_connection import FileConnection
from encodapy.utils.models import InputDataEntityModel, StaticDataEntityModel
from encodapy.utils.units import DataUnits, TimeUnits


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_file_connection_with_config():
    """Create a FileConnection instance with fully mocked dependencies for testing.

    All external dependencies are replaced with MagicMock instances to enable
    isolated unit testing of the FileConnection data query methods.

    Returns:
        FileConnection: Instance with mocked connection parameters, config, and file paths.
    """

    connection = FileConnection()

    # Mock connection parameters
    connection.file_params = MagicMock(spec=FileEnvVariables)
    connection.file_params.path_of_input_file = "/test/input.csv"
    connection.file_params.path_of_static_data = "/test/static.json"
    connection.file_params.path_of_results = "/test/results"

    # Mock config with proper structure
    connection.config = MagicMock()
    connection.config.controller_settings = MagicMock()
    connection.config.controller_settings.time_settings = MagicMock()
    connection.config.controller_settings.time_settings.calculation = MagicMock()
    connection.config.controller_settings.time_settings.calculation.timestep = 60
    connection.config.controller_settings.time_settings.calculation.timestep_unit = TimeUnits.MINUTE
    connection.config.controller_settings.time_settings.calibration = MagicMock()
    connection.config.controller_settings.time_settings.calibration.timestep = 1
    connection.config.controller_settings.time_settings.calibration.timestep_unit = TimeUnits.SECOND

    return connection


@pytest.fixture
def sample_csv_content():
    """Create sample CSV content for testing.

    Returns:
        str: CSV content as string.
    """
    return """Time;temperature;humidity
2024-01-15 10:00:00;20.5;65.0
2024-01-15 10:15:00;21.0;66.0
2024-01-15 10:30:00;21.5;67.0
2024-01-15 10:45:00;22.0;68.0
"""


@pytest.fixture
def sample_json_content():
    """Create sample JSON content for testing.

    Returns:
        str: JSON content as string.
    """
    return json.dumps({
        "data": [
            {
                "id": "TestEntity:001",
                "attributes": [
                    {
                        "id": "temperature",
                        "value": 20.5,
                        "unit": "CEL",
                        "time": "2024-01-15T10:00:00Z"
                    },
                    {
                        "id": "humidity",
                        "value": 65.0,
                        "unit": "P1",
                        "time": "2024-01-15T10:00:00Z"
                    }
                ]
            }
        ]
    }, indent=2)


@pytest.fixture
def mock_input_entity_timeseries():
    """Create a mock InputModel entity with timeseries attributes for testing.

    Returns:
        InputModel: Mock input entity with timeseries attributes.
    """
    return InputModel(
        id="test_entity",
        interface=Interfaces.FILE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.TIMESERIES,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="humidity",
                id_interface="humidity",
                type=AttributeTypes.TIMESERIES,
                value=None,
                unit=DataUnits.PERCENT,
            ),
        ],
    )


@pytest.fixture
def mock_input_entity_values():
    """Create a mock InputModel entity with value attributes for testing.

    Returns:
        InputModel: Mock input entity with value attributes.
    """
    return InputModel(
        id="test_entity_values",
        interface=Interfaces.FILE,
        id_interface="TestEntity:002",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="pressure",
                id_interface="pressure",
                type=AttributeTypes.VALUE,
                value=None,
                unit=DataUnits.VLT,
            ),
        ],
    )


# =============================================================================
# Tests for _read_time_from_string
# =============================================================================


def test_read_time_from_string_none():
    """Test _read_time_from_string with None input.

    Verifies that the method handles None input gracefully.

    Asserts:
        - Result is None
    """
    connection = FileConnection()
    result = connection._read_time_from_string(None)
    assert result is None


def test_read_time_from_string_datetime_with_tz():
    """Test _read_time_from_string with datetime that already has timezone.

    Verifies that datetime objects with timezone info are returned unchanged.

    Asserts:
        - Result is the same datetime object
        - Timezone is preserved
    """
    connection = FileConnection()
    input_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = connection._read_time_from_string(input_time)
    assert result == input_time


def test_read_time_from_string_datetime_without_tz():
    """Test _read_time_from_string with datetime without timezone.

    Verifies that datetime objects without timezone info get local timezone assigned.

    Asserts:
        - Result has timezone info
        - Time value is preserved
    """
    connection = FileConnection()
    input_time = datetime(2024, 1, 15, 10, 30, 0)
    result = connection._read_time_from_string(input_time)
    assert result is not None
    assert result.tzinfo is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_read_time_from_string_iso_format():
    """Test _read_time_from_string with ISO 8601 format string.

    Verifies that ISO 8601 formatted time strings are parsed correctly.

    Asserts:
        - Result is a datetime object
        - Time values are correct
    """
    connection = FileConnection()
    time_string = "2024-01-15T10:30:00Z"
    result = connection._read_time_from_string(time_string)
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 10
    assert result.minute == 30


def test_read_time_from_string_iso_format_with_timezone():
    """Test _read_time_from_string with ISO 8601 format string with timezone offset.

    Verifies that ISO 8601 formatted time strings with timezone are parsed correctly.

    Asserts:
        - Result is a datetime object
        - Time values are correct
        - Timezone is set
    """
    connection = FileConnection()
    time_string = "2024-01-15T10:30:00+02:00"
    result = connection._read_time_from_string(time_string)
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_read_time_from_string_invalid_format():
    """Test _read_time_from_string with invalid time format.

    Verifies that invalid time string formats are handled gracefully.

    Asserts:
        - Result is None
    """
    connection = FileConnection()
    time_string = "invalid-time-format"
    result = connection._read_time_from_string(time_string)
    assert result is None


# =============================================================================
# Tests for get_data_from_csv_file
# =============================================================================


def test_get_data_from_csv_file_success_with_example_data(mock_file_connection_with_config):
    """Test get_data_from_csv_file with real example CSV data.

    Verifies successful CSV data retrieval and processing using the actual example
    CSV file from the examples directory.

    Uses the real example file: inputs_csv-file_interface_example.csv

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is InputDataEntityModel
        - Entity ID is correct
        - Attributes are populated with real data
    """



    # Use the real example CSV file
    example_csv_path = (
        "C:\\Users\\marti\\Downloads\\encodapy\\examples\\03_interfaces\\"
        "inputs_csv-file_interface_example.csv"
    )

    if not os.path.exists(example_csv_path):
        pytest.skip(f"Example CSV file not found: {example_csv_path}")

    # Create an entity that matches the example CSV structure
    entity = InputModel(
        id="input_fiware_01",
        interface=Interfaces.FILE,
        id_interface="urn:input_fiware:01",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="urn:input_fiware:01.temperature",
                type=AttributeTypes.TIMESERIES,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="power",
                id_interface="urn:input_fiware:01.power",
                type=AttributeTypes.TIMESERIES,
                value=None,
                unit=DataUnits.WTT,
            ),
        ],
    )

    # Update the file path in the connection
    mock_file_connection_with_config.file_params.path_of_input_file = example_csv_path

    result = mock_file_connection_with_config.get_data_from_csv_file(
        method=DataQueryTypes.CALCULATION,
        entity=entity
    )

    # Note: This might fail due to pandas timestamp handling issues in the current implementation
    # If so, the test will fail and we'll know we need to fix the implementation
    assert result is not None
    assert isinstance(result, InputDataEntityModel)
    # Note: The implementation uses entity.id, not entity.id_interface
    assert result.id == "input_fiware_01"
    assert len(result.attributes) == 2

    # Check that attributes have the correct IDs
    attr_ids = [attr.id for attr in result.attributes]
    assert "temperature" in attr_ids
    assert "power" in attr_ids

    # Check that we got some data (timestamps and values)
    # Note: The data might be resampled based on time settings, so we don't check exact count
    for attr in result.attributes:
        assert attr.data_available is True
        assert len(attr.data) > 0  # We got some data points


def test_get_data_from_csv_file_file_not_found(mock_file_connection_with_config):
    """Test get_data_from_csv_file with non-existent file.

    Verifies graceful handling of file not found errors.

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is None
        - No exception is raised
    """


    # Set non-existent file path
    mock_file_connection_with_config.file_params.path_of_input_file = "/non/existent/file.csv"

    entity = InputModel(
        id="test_entity",
        interface=Interfaces.FILE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.TIMESERIES,
            ),
        ],
    )

    result = mock_file_connection_with_config.get_data_from_csv_file(
        method=DataQueryTypes.CALCULATION,
        entity=entity
    )

    assert result is None


def test_get_data_from_csv_file_empty_file(mock_file_connection_with_config):
    """Test get_data_from_csv_file with empty CSV file.

    Verifies graceful handling of empty CSV files.

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is None
    """


    # Create empty CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("")  # Empty file
        temp_path = f.name

    try:
        mock_file_connection_with_config.file_params.path_of_input_file = temp_path

        entity = InputModel(
            id="test_entity",
            interface=Interfaces.FILE,
            id_interface="TestEntity:001",
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temperature",
                    type=AttributeTypes.TIMESERIES,
                ),
            ],
        )

        result = mock_file_connection_with_config.get_data_from_csv_file(
            method=DataQueryTypes.CALCULATION,
            entity=entity
        )

        assert result is None

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_get_data_from_json_file_success_with_example_data(mock_file_connection_with_config):
    """Test _get_data_from_json_file with real example JSON data.

    Verifies successful JSON data retrieval and processing using the actual example
    JSON file from the examples directory.

    Uses the real example file: inputs_json-file_interface_example.json

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is InputDataEntityModel
        - Entity ID is correct
        - Attributes are populated with real data
    """



    # Use the real example JSON file
    example_json_path = (
        "C:\\Users\\marti\\Downloads\\encodapy\\examples\\03_interfaces\\"
        "inputs_json-file_interface_example.json"
    )

    if not os.path.exists(example_json_path):
        pytest.skip(f"Example JSON file not found: {example_json_path}")

    # Create an entity that matches the example JSON structure
    entity = InputModel(
        id="input_fiware_01",
        interface=Interfaces.FILE,
        id_interface="urn:input_fiware:01",  # This must match the JSON entity id
        attributes=[
            AttributeModel(
                id="temperature_01",
                id_interface="temperature:01",  # This must match the JSON attribute id
                type=AttributeTypes.VALUE,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="temperature_02",
                id_interface="temperature:02",  # This must match the JSON attribute id
                type=AttributeTypes.VALUE,
                value=None,
                unit=DataUnits.DEGREECELSIUS,
            ),
        ],
    )

    # Update the file path in the connection
    mock_file_connection_with_config.file_params.path_of_input_file = example_json_path

    result = mock_file_connection_with_config.get_data_from_json_file(
        method=DataQueryTypes.CALCULATION,
        entity=entity
    )

    # Note: This might fail due to data structure issues, but we're testing with real data
    assert result is not None
    assert isinstance(result, InputDataEntityModel)
    # Note: The implementation uses entity.id, not entity.id_interface
    assert result.id == "input_fiware_01"
    assert len(result.attributes) == 2

    # Check that attributes have the correct IDs
    attr_ids = [attr.id for attr in result.attributes]
    assert "temperature_01" in attr_ids
    assert "temperature_02" in attr_ids

    # Check that we got the data from the example file
    for attr in result.attributes:
        assert attr.data_available is True


# =============================================================================
# Tests for _get_data_from_json_file
# =============================================================================


def test_get_static_data_from_file_with_example_data(mock_file_connection_with_config):
    """Test get_staticdata_from_file with real example static data JSON.

    Verifies successful static data retrieval and processing using the actual example
    static data JSON file from the examples directory.

    Uses the real example file: static_data.json

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is StaticDataEntityModel
        - Entity ID is correct
        - Attributes are populated with real data
    """



    # Use the real example static data JSON file
    example_static_path = (
        "C:\\Users\\marti\\Downloads\\encodapy\\examples\\03_interfaces\\"
        "static_data.json"
    )

    if not os.path.exists(example_static_path):
        pytest.skip(f"Example static data file not found: {example_static_path}")

    # Create an entity that matches the example static data structure
    entity = StaticDataModel(
        id="thermal_storage",
        interface=Interfaces.FILE,
        id_interface="thermal_storage",  # This must match the JSON entity id
        attributes=[
            AttributeModel(
                id="volume",
                id_interface="volume",  # This must match the JSON attribute id
                type=AttributeTypes.VALUE,
                value=500,
                unit=DataUnits.LITER,
            ),
            AttributeModel(
                id="medium",
                id_interface="medium",  # This must match the JSON attribute id
                type=AttributeTypes.VALUE,
                value="water",
                unit=None,
            ),
        ],
    )

    # Update the file path in the connection
    mock_file_connection_with_config.file_params.path_of_static_data = example_static_path

    result = mock_file_connection_with_config.get_staticdata_from_file(entity=entity)

    # Note: This might fail due to data structure issues, but we're testing with real data
    assert result is not None
    assert isinstance(result, StaticDataEntityModel)
    assert result.id == "thermal_storage"
    assert len(result.attributes) == 2

    # Check that attributes have the correct IDs
    attr_ids = [attr.id for attr in result.attributes]
    assert "volume" in attr_ids
    assert "medium" in attr_ids

    # Check that we got the data from the example file
    for attr in result.attributes:
        assert attr.data_available is True


def test_get_data_from_json_file_not_found(mock_file_connection_with_config):
    """Test _get_data_from_json_file with non-existent file.

    Verifies graceful handling of file not found errors.

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is None
    """


    entity = StaticDataModel(
        id="test_static",
        interface=Interfaces.FILE,
        id_interface="StaticEntity:001",
        attributes=[
            AttributeModel(
                id="setpoint",
                id_interface="setpoint",
                type=AttributeTypes.VALUE,
            ),
        ],
    )

    result = mock_file_connection_with_config._get_data_from_json_file(
        entity=entity,
        path_of_file="/non/existent/file.json",
        data_type="staticdata"
    )

    assert result is None


def test_get_data_from_json_file_invalid_json(mock_file_connection_with_config):
    """Test _get_data_from_json_file with invalid JSON content.

    Verifies graceful handling of invalid JSON content.

    Args:
        mock_file_connection_with_config: Fixture with mocked FileConnection

    Asserts:
        - Result is None
    """


    # Create file with invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json content }")
        temp_path = f.name

    try:
        entity = StaticDataModel(
            id="test_static",
            interface=Interfaces.FILE,
            id_interface="StaticEntity:001",
            attributes=[
                AttributeModel(
                    id="setpoint",
                    id_interface="setpoint",
                    type=AttributeTypes.VALUE,
                ),
            ],
        )

        result = mock_file_connection_with_config._get_data_from_json_file(
            entity=entity,
            path_of_file=temp_path,
            data_type="staticdata"
        )

        assert result is None

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
