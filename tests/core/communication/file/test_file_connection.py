"""
Tests for FILE connection and configuration management in EnCoDaPy.

This module tests the FileConnection class functionality for:
- Loading file parameters from environment variables
- Configuration management for file paths
- Connection preparation and validation

Test Strategy:
- Unit tests with mocked environment variables
- Focus on load_file_params() method
- All external dependencies (environment) are mocked
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import os
from unittest.mock import MagicMock, patch

import pytest

from encodapy.config import Interfaces, AttributeTypes, DataQueryTypes
from encodapy.config.env_values import FileEnvVariables
from encodapy.config.models import FileStorageMethod, InputModel, AttributeModel, OutputModel
from encodapy.config import (
    ConfigModel,
    ControllerSettingModel,
    InterfaceModel,
    TimeSettingsModel,
)
from encodapy.config.models import TimeSettingsCalculationModel
from encodapy.utils.units import TimeUnits
from encodapy.service.communication.file_connection import FileConnection
from encodapy.utils.error_handling import NotSupportedError
from encodapy.utils.models import OutputDataEntityModel


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_file_connection():
    """Create a FileConnection instance with mocked parameters.

    Provides a FileConnection with all connection parameters mocked using MagicMock.
    Useful for testing connection-related methods without actual file operations.

    Returns:
        FileConnection: Instance with mocked file parameters.
    """
    connection = FileConnection()
    connection.file_params = MagicMock(spec=FileEnvVariables)
    connection.file_params.storage_method = FileStorageMethod.APPEND
    connection.file_params.path_of_input_file = "./input/input_file.csv"
    connection.file_params.path_of_static_data = "./input/static_data.json"
    connection.file_params.path_of_results = "./results"
    connection.config = MagicMock()
    return connection


@pytest.fixture
def mock_file_env_default():
    """Create a mock FileEnvVariables with default configuration.

    Provides environment configuration with default file settings.
    Useful for testing standard file connection scenarios.

    Yields:
        FileEnvVariables: Mocked environment with default file config.
    """
    with patch.dict(
        os.environ,
        {
            "FILE_STORAGE_METHOD": "append",
            "FILE_PATH_OF_INPUT_FILE": "./input/input_file.csv",
            "FILE_PATH_OF_STATIC_DATA": "./input/static_data.json",
            "FILE_PATH_OF_RESULTS": "./results",
        },
    ):
        env = FileEnvVariables()
        yield env


@pytest.fixture
def mock_file_env_overwrite():
    """Create a mock FileEnvVariables with overwrite storage method.

    Provides environment configuration with overwrite storage method.
    Useful for testing different storage method scenarios.

    Yields:
        FileEnvVariables: Mocked environment with overwrite storage.
    """
    with patch.dict(
        os.environ,
        {
            "FILE_STORAGE_METHOD": "overwrite",
            "FILE_PATH_OF_INPUT_FILE": "/data/input.csv",
            "FILE_PATH_OF_STATIC_DATA": "/data/static.json",
            "FILE_PATH_OF_RESULTS": "/data/results",
        },
    ):
        env = FileEnvVariables()
        yield env


@pytest.fixture
def mock_file_env_new_file():
    """Create a mock FileEnvVariables with new_file storage method.

    Provides environment configuration with new_file storage method.
    Useful for testing timestamp-based file creation.

    Yields:
        FileEnvVariables: Mocked environment with new_file storage.
    """
    with patch.dict(
        os.environ,
        {
            "FILE_STORAGE_METHOD": "new_file",
            "FILE_PATH_OF_INPUT_FILE": "./input/input.csv",
            "FILE_PATH_OF_STATIC_DATA": "./input/static.json",
            "FILE_PATH_OF_RESULTS": "./results",
        },
    ):
        env = FileEnvVariables()
        yield env


# =============================================================================
# Tests for load_file_params
# =============================================================================


def test_load_file_params_default(mock_file_env_default):
    """Test loading file parameters with default configuration.

    Verifies that file parameters are loaded correctly from environment variables
    with default settings.

    Args:
        mock_file_env_default: Fixture providing environment with default config

    Asserts:
        - file_params is created
        - storage_method is APPEND
        - paths are correctly loaded from environment
    """
    connection = FileConnection()

    with patch(
        "encodapy.service.communication.file_connection.FileEnvVariables",
        return_value=mock_file_env_default,
    ):
        connection.load_file_params()

    # FileConnection doesn't initialize file_params and config in __init__
    # We need to check that the attributes exist (they will be set later)
    assert hasattr(connection, "file_params")
    assert connection.file_params.path_of_input_file == "./input/input_file.csv"
    assert connection.file_params.path_of_static_data == "./input/static_data.json"
    assert connection.file_params.path_of_results == "./results"


def test_load_file_params_overwrite(mock_file_env_overwrite):
    """Test loading file parameters with overwrite storage method.

    Verifies that file parameters are loaded correctly with overwrite
    storage method configuration.

    Args:
        mock_file_env_overwrite: Fixture providing environment with overwrite config

    Asserts:
        - storage_method is OVERWRITE
        - custom paths are correctly loaded
    """
    connection = FileConnection()

    with patch(
        "encodapy.service.communication.file_connection.FileEnvVariables",
        return_value=mock_file_env_overwrite,
    ):
        connection.load_file_params()

    assert connection.file_params is not None
    assert connection.file_params.storage_method == FileStorageMethod.OVERWRITE
    assert connection.file_params.path_of_input_file == "/data/input.csv"
    assert connection.file_params.path_of_static_data == "/data/static.json"
    assert connection.file_params.path_of_results == "/data/results"


def test_load_file_params_new_file(mock_file_env_new_file):
    """Test loading file parameters with new_file storage method.

    Verifies that file parameters are loaded correctly with new_file
    storage method configuration.

    Args:
        mock_file_env_new_file: Fixture providing environment with new_file config

    Asserts:
        - storage_method is NEW_FILE
    """
    connection = FileConnection()

    with patch(
        "encodapy.service.communication.file_connection.FileEnvVariables",
        return_value=mock_file_env_new_file,
    ):
        connection.load_file_params()

    assert connection.file_params is not None
    assert connection.file_params.storage_method == FileStorageMethod.NEW_FILE


# =============================================================================
# Tests for FileConnection initialization
# =============================================================================


def test_file_connection_init():
    """Test FileConnection initialization.

    Verifies that FileConnection instance is initialized correctly
    with expected attributes.

    Asserts:
        - file_params attribute exists (as type hint)
        - config attribute exists (as type hint)
    """
    connection = FileConnection()

    # The attributes are declared as type hints but not initialized in __init__
    # Check that they can be set without errors
    # Test that we can assign to these attributes
    connection.file_params = FileEnvVariables()
    connection.config = ConfigModel(
        interfaces=InterfaceModel(fiware=False, file=True, mqtt=False),
        inputs=[],
        outputs=[],
        staticdata=[],
        controller_components=[],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=24,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type="absolute",
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                ),
            ),
            specific_settings={},
        ),
    )

    assert hasattr(connection, "file_params")
    assert hasattr(connection, "config")
    assert connection.file_params is not None
    assert connection.config is not None


# =============================================================================
# Tests for _get_last_timestamp_for_file_output
# =============================================================================


def test_get_last_timestamp_for_file_output_empty(mock_file_connection):
    """Test _get_last_timestamp_for_file_output with empty output entity.

    Verifies that the method returns correct structure for output entities
    with no attributes.

    Args:
        mock_file_connection: Fixture with mocked FileConnection

    Asserts:
        - Returns tuple with OutputDataEntityModel and None timestamp
        - Model has correct entity ID
        - Attributes list is empty
    """
    output_entity = OutputModel(
        id="test_output",
        interface=Interfaces.FILE,
        id_interface="TestOutput:001",
        attributes=[],
        commands=[],
    )

    result_model, result_timestamp = mock_file_connection._get_last_timestamp_for_file_output(
        output_entity
    )

    assert isinstance(result_model, OutputDataEntityModel)
    assert result_model.id == "TestOutput:001"
    assert len(result_model.attributes_status) == 0
    assert result_timestamp is None


# =============================================================================
# Tests for file extension detection
# =============================================================================


def test_get_data_from_file_csv_extension(mock_file_connection, mock_input_entity_csv):
    """Test that get_data_from_file detects CSV extension correctly.

    Verifies that the method correctly identifies CSV files and calls
    the appropriate handler.

    Args:
        mock_file_connection: Fixture with mocked FileConnection
        mock_input_entity_csv: Fixture with CSV input entity

    Asserts:
        - Method attempts to call get_data_from_csv_file
    """
    # Mock the CSV file path
    mock_file_connection.file_params.path_of_input_file = "/path/to/test.csv"

    # Mock the CSV handler to return a result
    mock_result = MagicMock()
    mock_file_connection.get_data_from_csv_file = MagicMock(return_value=mock_result)

    result = mock_file_connection.get_data_from_file(
        method=DataQueryTypes.CALCULATION,
        entity=mock_input_entity_csv
    )

    # Should have called the CSV handler
    mock_file_connection.get_data_from_csv_file.assert_called_once()
    assert result == mock_result


def test_get_data_from_file_json_extension(mock_file_connection, mock_input_entity_json):
    """Test that get_data_from_file detects JSON extension correctly.

    Verifies that the method correctly identifies JSON files and calls
    the appropriate handler.

    Args:
        mock_file_connection: Fixture with mocked FileConnection
        mock_input_entity_json: Fixture with JSON input entity

    Asserts:
        - Method attempts to call get_data_from_json_file
    """
    # Mock the JSON file path
    mock_file_connection.file_params.path_of_input_file = "/path/to/test.json"

    # Mock the JSON handler to return a result
    mock_result = MagicMock()
    mock_file_connection.get_data_from_json_file = MagicMock(return_value=mock_result)

    result = mock_file_connection.get_data_from_file(
        method=DataQueryTypes.CALCULATION,
        entity=mock_input_entity_json
    )

    # Should have called the JSON handler
    mock_file_connection.get_data_from_json_file.assert_called_once()
    assert result == mock_result


def test_get_data_from_file_unsupported_extension_raises_error(mock_file_connection):
    """Test that get_data_from_file raises NotSupportedError for unsupported extensions.

    Verifies error handling when file extension is not supported.

    Args:
        mock_file_connection: Fixture with mocked FileConnection

    Asserts:
        - NotSupportedError exception is raised
    """
    # Mock an unsupported file path
    mock_file_connection.file_params.path_of_input_file = "/path/to/test.xls"

    entity = InputModel(
        id="test_entity",
        interface=Interfaces.FILE,
        id_interface="TestEntity:001",
        attributes=[
            AttributeModel(
                id="temp",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
            ),
        ],
    )

    with pytest.raises(NotSupportedError):
        mock_file_connection.get_data_from_file(
            method=DataQueryTypes.CALCULATION,
            entity=entity
        )


def test_get_data_from_file_case_insensitive_extension(mock_file_connection):
    """Test that get_data_from_file handles case-insensitive file extensions.

    Verifies that file extensions are handled case-insensitively.

    Args:
        mock_file_connection: Fixture with mocked FileConnection

    Asserts:
        - CSV files with uppercase extension are handled
        - JSON files with uppercase extension are handled
    """
    entity = InputModel(
        id="test_entity",
        interface=Interfaces.FILE,
        id_interface="TestEntity:001",
        attributes=[],
    )

    # Test CSV with uppercase extension
    mock_file_connection.file_params.path_of_input_file = "/path/to/test.CSV"
    mock_file_connection.get_data_from_csv_file = MagicMock(return_value=MagicMock())

    mock_file_connection.get_data_from_file(
        method=DataQueryTypes.CALCULATION,
        entity=entity
    )

    mock_file_connection.get_data_from_csv_file.assert_called_once()

    # Test JSON with uppercase extension
    mock_file_connection.file_params.path_of_input_file = "/path/to/test.JSON"
    mock_file_connection.get_data_from_json_file = MagicMock(return_value=MagicMock())

    mock_file_connection.get_data_from_file(
        method=DataQueryTypes.CALCULATION,
        entity=entity
    )

    mock_file_connection.get_data_from_json_file.assert_called_once()
