"""
Shared fixtures for FILE unit tests.

This module provides common fixtures used across multiple FILE-related unit test files.
Fixtures here are designed for isolated unit testing with mocked dependencies.
"""

# pylint: disable=redefined-outer-name,unused-import
import os
import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from encodapy.config import (
    ConfigModel,
    ControllerSettingModel,
    InterfaceModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsModel,
    TimeSettingsResultsModel,
    AttributeModel,
    AttributeTypes,
    InputModel,
    OutputModel,
    StaticDataModel,
    Interfaces,
)
from encodapy.config.env_values import FileEnvVariables
from encodapy.utils.units import TimeUnits, DataUnits


@pytest.fixture
def mock_config():
    """Create a minimal ConfigModel instance for unit testing.

    Returns:
        ConfigModel: Minimal configuration with FILE interface enabled
            and default time settings for testing.
    """
    return ConfigModel(
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
                calibration=TimeSettingsCalibrationModel(
                    timerange=24,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type="absolute",
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


@pytest.fixture
def mock_file_env_vars():
    """Create a mock FileEnvVariables with default values for testing.

    Provides environment configuration for file interface testing.

    Returns:
        FileEnvVariables: Mocked environment with default file paths.
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
def mock_file_env_vars_custom():
    """Create a mock FileEnvVariables with custom values for testing.

    Provides environment configuration with custom file paths.

    Returns:
        FileEnvVariables: Mocked environment with custom file paths.
    """
    with patch.dict(
        os.environ,
        {
            "FILE_STORAGE_METHOD": "overwrite",
            "FILE_PATH_OF_INPUT_FILE": "/custom/path/input.csv",
            "FILE_PATH_OF_STATIC_DATA": "/custom/path/static.json",
            "FILE_PATH_OF_RESULTS": "/custom/path/results",
        },
    ):
        env = FileEnvVariables()
        yield env


@pytest.fixture
def mock_controller_settings():
    """Create a minimal ControllerSettingModel for unit testing.

    This fixture provides just the controller settings part for tests
    that need to set conn.config.controller_settings directly.

    Returns:
        ControllerSettingModel: Configuration with time settings.
    """
    return ControllerSettingModel(
        time_settings=TimeSettingsModel(
            calculation=TimeSettingsCalculationModel(
                timerange=24,
                timerange_unit=TimeUnits.HOUR,
                timerange_type="absolute",
                timestep=60,
                timestep_unit=TimeUnits.MINUTE,
                sampling_time=1,
                sampling_time_unit=TimeUnits.MINUTE,
            ),
            calibration=TimeSettingsCalibrationModel(
                timerange=24,
                timerange_unit=TimeUnits.HOUR,
                timerange_type="absolute",
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
    )


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing.

    Creates a CSV file with sample time-series data.

    Returns:
        str: Path to the temporary CSV file.
    """
    # Create sample CSV data
    csv_data = """Time;temperature;humidity
2024-01-15 10:00:00;20.5;65.0
2024-01-15 10:15:00;21.0;66.0
2024-01-15 10:30:00;21.5;67.0
2024-01-15 10:45:00;22.0;68.0
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_data)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_json_file():
    """Create a temporary JSON file for testing.

    Creates a JSON file with sample data.

    Returns:
        str: Path to the temporary JSON file.
    """
    json_data = {
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
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(json_data, f, indent=2)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_results_dir():
    """Create a temporary results directory for testing.

    Returns:
        str: Path to the temporary results directory.
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def mock_input_entity_csv():
    """Create a mock InputModel entity for CSV data query testing.

    Provides a standardized test entity with temperature and humidity attributes
    for testing CSV data retrieval scenarios.

    Returns:
        InputModel: Mock input entity with time-series attributes.
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
def mock_input_entity_json():
    """Create a mock InputModel entity for JSON data query testing.

    Provides a standardized test entity for JSON data retrieval scenarios.

    Returns:
        InputModel: Mock input entity with value attributes.
    """
    return InputModel(
        id="test_entity_json",
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


@pytest.fixture
def mock_static_data_entity():
    """Create a mock StaticDataModel entity for static data testing.

    Provides a standardized test entity for static data retrieval scenarios.

    Returns:
        StaticDataModel: Mock static data entity.
    """
    return StaticDataModel(
        id="test_static",
        interface=Interfaces.FILE,
        id_interface="StaticEntity:001",
        attributes=[
            AttributeModel(
                id="setpoint",
                id_interface="setpoint",
                type=AttributeTypes.VALUE,
                value=22.0,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="max_limit",
                id_interface="max_limit",
                type=AttributeTypes.VALUE,
                value=30.0,
                unit=DataUnits.DEGREECELSIUS,
            ),
        ],
    )


@pytest.fixture
def mock_output_entity():
    """Create a mock OutputModel entity for data sending testing.

    Provides a standardized test entity with result attributes for testing
    output data scenarios.

    Returns:
        OutputModel: Mock output entity with result attributes.
    """
    return OutputModel(
        id="test_output",
        interface=Interfaces.FILE,
        id_interface="TestOutput:001",
        attributes=[
            AttributeModel(
                id="result",
                id_interface="result",
                type=AttributeTypes.VALUE,
                value=42.0,
                unit=DataUnits.DEGREECELSIUS,
            ),
            AttributeModel(
                id="status",
                id_interface="status",
                type=AttributeTypes.VALUE,
                value="active",
                unit=None,
            ),
        ],
        commands=[],
    )


@pytest.fixture
def sample_csv_dataframe():
    """Create a sample pandas DataFrame for CSV testing.

    Returns:
        pd.DataFrame: Sample DataFrame with time index and temperature data.
    """
    df = pd.DataFrame({
        "Time": [
            "2024-01-15 10:00:00",
            "2024-01-15 10:15:00",
            "2024-01-15 10:30:00",
            "2024-01-15 10:45:00",
        ],
        "temperature": [20.5, 21.0, 21.5, 22.0],
        "humidity": [65.0, 66.0, 67.0, 68.0],
    })
    df["Time"] = pd.to_datetime(df["Time"])
    df.set_index("Time", inplace=True)
    return df
