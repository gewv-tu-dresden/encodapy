"""
Tests for FIWARE data sending functionality in EnCoDaPy.

This module tests the data sending logic to FIWARE Context Broker,
including:
- Unit adjustment and conversion for FIWARE compatibility
- Entity creation and attribute updates
- Data formatting and metadata handling
- Error handling for data sending operations

Test Strategy:
- Unit tests with mocked FIWARE clients
- Focus on _adjust_units_for_fiware() method
- Tests for data sending with various attribute types (value, timeseries)
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import pandas as pd

from encodapy.config import AttributeTypes, Interfaces
from encodapy.config.models import (
    AttributeModel,
    CommandModel,
    OutputModel,
    ConfigModel,
    TimeSettingsCalculationModel,
    TimeSettingsModel,
    ControllerSettingModel,
)
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.units import DataUnits
from encodapy.utils.models import (
    FiwareConnectionParameter,
    FiwareParameter,
    DatabaseParameter,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_fiware_connection_full():
    """Create a fully mocked FiwareConnection instance for data sending tests.
    
    Provides a complete FiwareConnection with all dependencies mocked:
    - Connection parameters (FIWARE and database)
    - ContextBrokerClient and CrateDBConnection clients
    - Configuration with time settings
    
    Returns:
        FiwareConnection: Fully mocked instance ready for unit testing.
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
    connection.fiware_conn_params.database_params.crate_db_user = "test_user"
    connection.fiware_conn_params.database_params.crate_db_pw = "test_pw"
    connection.fiware_conn_params.database_params.crate_db_ssl = False

    # Mock clients
    connection.cb_client = MagicMock()
    connection.crate_db_client = MagicMock()

    # Mock config with proper structure
    connection.config = MagicMock(spec=ConfigModel)
    connection.config.controller_settings = MagicMock(spec=ControllerSettingModel)
    connection.config.controller_settings.time_settings = MagicMock(spec=TimeSettingsModel)
    connection.config.controller_settings.time_settings.calculation = MagicMock(
        spec=TimeSettingsCalculationModel
    )
    connection.config.controller_settings.time_settings.calculation.timestep = 60
    connection.config.controller_settings.time_settings.calculation.timestep_unit = "minute"
    connection.config.controller_settings.time_settings.calibration = None

    return connection


@pytest.fixture
def mock_output_entity():
    """Create a mock OutputModel entity for data sending tests.
    
    Provides a standardized test entity with temperature attribute for testing
    value-based data sending scenarios.
    
    Returns:
        OutputModel: Mock output entity with temperature value in Celsius.
    """
    return OutputModel(
        id="test_output",
        interface=Interfaces.FIWARE,
        id_interface="TestOutput:001",
        attributes=[
            AttributeModel(
                id="temperature",
                id_interface="temperature",
                type=AttributeTypes.VALUE,
                value=22.5,
                unit=DataUnits.DEGREECELSIUS,
                timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            ),
        ],
    )


@pytest.fixture
def mock_output_entity_with_dataframe():
    """Create a mock OutputModel entity with DataFrame attribute for timeseries testing.
    
    Provides a test entity with pandas DataFrame for testing timeseries data
    sending scenarios.
    
    Returns:
        OutputModel: Mock output entity with timeseries temperature data.
    """
    # Create a DataFrame for timeseries data
    df = pd.DataFrame({
        "time": pd.date_range("2024-01-15 10:00:00", periods=3, freq="10min"),
        "temperature": [20.0, 21.0, 22.0],
    })
    df.set_index("time", inplace=True)

    return OutputModel(
        id="test_output_ts",
        interface=Interfaces.FIWARE,
        id_interface="TestOutputTS:001",
        attributes=[
            AttributeModel(
                id="temperature_ts",
                id_interface="temperature",
                type=AttributeTypes.TIMESERIES,
                value=df,
                unit=DataUnits.DEGREECELSIUS,
            ),
        ],
    )


@pytest.fixture
def mock_output_commands():
    """Create mock output commands for testing command sending functionality.
    
    Returns:
        list: List of CommandModel instances for testing.
    """
    return [
        CommandModel(
            id="cmd1",
            id_interface="command1",
            value="ON",
        ),
    ]


@pytest.fixture
def mock_fiware_entity():
    """Create a mock FIWARE entity for testing.
    
    Returns:
        MagicMock: Mocked FIWARE entity with ID and type.
    """
    entity = MagicMock()
    entity.id = "TestOutput:001"
    entity.type = "TestOutput"
    return entity


@pytest.fixture
def mock_entity_attributes():
    """Create mock entity attributes with unit metadata for testing.
    
    Returns:
        dict: Dictionary of mock attributes with unitCode metadata.
    """
    attrs = {}

    temp_attr = MagicMock()
    temp_attr.name = "temperature"
    temp_attr.type = "Number"
    temp_attr.metadata = {"unitCode": MagicMock(value="CEL")}
    attrs["temperature"] = temp_attr

    return attrs


# =============================================================================
# Tests for _adjust_units_for_fiware
# =============================================================================


def test_adjust_units_for_fiware_converts_value_and_metadata():
    """Test that _adjust_units_for_fiware converts value and metadata correctly.
    
    Verifies successful unit conversion from Watts to Kilowatts with proper metadata.
    This is the primary use case for unit adjustment when sending data to FIWARE.
    
    Args:
        attribute: AttributeModel with value=1000.0, unit=WTT (Watts)
        fiware_unit: DataUnits.KWT (Kilowatts)
    
    Asserts:
        - Value is converted from 1000W to 1kW (1000.0 -> 1.0)
        - Unit is changed to KWT
        - Metadata contains unitCode with KWT value
    """
    connection = FiwareConnection()
    attribute = AttributeModel(
        id="power",
        id_interface="power",
        value=1000.0,
        unit=DataUnits.WTT,
    )

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.KWT,
    )

    assert adjusted_attribute.value == pytest.approx(1.0)
    assert adjusted_attribute.unit == DataUnits.KWT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.KWT.value
        for item in metadata
    )


def test_adjust_units_for_fiware_preserves_original_on_failure():
    """Test that _adjust_units_for_fiware preserves original unit on conversion failure.
    
    Verifies graceful handling when unit conversion fails (e.g., Watts to Celsius).
    The method should preserve the original value and unit in this case.
    
    Args:
        attribute: AttributeModel with value=1000.0, unit=WTT (Watts)
        fiware_unit: DataUnits.DEGREECELSIUS (incompatible unit)
    
    Asserts:
        - Value remains unchanged (1000.0)
        - Unit remains WTT (not converted)
        - Metadata contains original unitCode (WTT)
    """
    connection = FiwareConnection()
    attribute = AttributeModel(
        id="power",
        id_interface="power",
        value=1000.0,
        unit=DataUnits.WTT,
    )

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.DEGREECELSIUS,  # Incompatible unit
    )

    assert adjusted_attribute.value == 1000.0
    assert adjusted_attribute.unit == DataUnits.WTT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.WTT.value
        for item in metadata
    )


def test_adjust_units_for_fiware_no_unit_no_fiware_unit():
    """Test _adjust_units_for_fiware when attribute has no unit and no fiware_unit.
    
    Verifies handling of unitless attributes. When neither the attribute nor
    the FIWARE entity specifies a unit, the method should return empty metadata.
    
    Args:
        attribute: AttributeModel with value=42.0, unit=None
        fiware_unit: None
    
    Asserts:
        - Value remains unchanged (42.0)
        - Unit remains None
        - Metadata is empty list
    """
    connection = FiwareConnection()
    attribute = AttributeModel(
        id="value",
        id_interface="value",
        value=42.0,
        unit=None,
    )

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="test",
        attribute=attribute,
        fiware_unit=None,
    )

    assert adjusted_attribute.value == 42.0
    assert adjusted_attribute.unit is None
    assert len(metadata) == 0


# =============================================================================
# Additional unit adjustment tests (merged from test_fiware_units.py)
# =============================================================================


def test_adjust_units_for_fiware_converts_watt_to_kilowatt():
    """Convertible values are transformed and metadata reflects the FIWARE unit.
    
    This is a focused test for the WTT to KWT conversion scenario, ensuring
    the unit conversion logic works correctly for power measurements.
    
    Asserts:
        - 1000W is converted to 1kW (value: 1000.0 -> 1.0)
        - Unit is changed to KWT
        - Metadata contains unitCode with KWT value
    """
    connection = FiwareConnection()
    attribute = AttributeModel(
        id="power",
        id_interface="power",
        value=1000.0,
        unit=DataUnits.WTT,
    )

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.KWT,
    )

    assert adjusted_attribute.value == pytest.approx(1.0)
    assert adjusted_attribute.unit == DataUnits.KWT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.KWT.value
        for item in metadata
    )


def test_adjust_units_for_fiware_preserves_actual_unit_metadata_on_failure():
    """On failed conversion, value and metadata keep the original physical unit.
    
    This test ensures that when unit conversion is not possible (e.g., power to temperature),
    the system gracefully falls back to the original unit rather than failing.
    
    Asserts:
        - Value remains unchanged (1000.0)
        - Unit remains WTT (original unit)
        - Metadata contains original unitCode (WTT)
    """
    connection = FiwareConnection()
    attribute = AttributeModel(
        id="power",
        id_interface="power",
        value=1000.0,
        unit=DataUnits.WTT,
    )

    adjusted_attribute, metadata = connection._adjust_units_for_fiware(
        id_output_entity="boiler",
        attribute=attribute,
        fiware_unit=DataUnits.DEGREECELSIUS,
    )

    assert adjusted_attribute.value == 1000.0
    assert adjusted_attribute.unit == DataUnits.WTT
    assert any(
        item.name == "unitCode" and item.value == DataUnits.WTT.value
        for item in metadata
    )
