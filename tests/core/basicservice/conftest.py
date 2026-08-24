"""
Pytest fixtures for ControllerBasicService tests.

This module provides common fixtures used across all test files for the
ControllerBasicService class in the encodapy.service.basic_service module.
"""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from filip.models.base import DataType

from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    BasicEnvVariables,
    CommandModel,
    ConfigModel,
    InterfaceModel,
    Interfaces,
    InputModel,
    OutputModel,
    StaticDataModel,
    TimeSettingsModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsResultsModel,
    ControllerSettingModel,
)
from encodapy.service.basic_service import ControllerBasicService
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataModel,
    OutputDataEntityModel,
    OutputDataModel,
)
from encodapy.utils.units import DataUnits, TimeUnits
from encodapy.config.env_values import FiwareEnvVariables, FileEnvVariables, MQTTEnvVariables


@pytest.fixture
def mock_fiware_env():
    """Fixture providing FiwareEnvVariables with default values for testing."""
    return FiwareEnvVariables(
        service="test_service",
        auth=False,
        cb_url="http://127.0.0.1:1026",
    )


@pytest.fixture
def mock_file_env():
    """Fixture providing FileEnvVariables with default values for testing."""
    return FileEnvVariables(
        input_path="./input",
        output_path="./output",
    )


@pytest.fixture
def mock_mqtt_env():
    """Fixture providing MQTTEnvVariables with default values for testing."""
    return MQTTEnvVariables(
        host="127.0.0.1",
        port=1883,
        client_id="test_client",
    )


def create_service_without_init():
    """
    Helper function to create a ControllerBasicService instance without
    calling __init__ to avoid the automatic prepare_basic_start call.
    
    This is useful for tests that need to test individual methods without
    the full initialization process.
    
    Returns:
        ControllerBasicService: Partially initialized service instance.
    """
    service = ControllerBasicService.__new__(ControllerBasicService)
    service.shutdown_event = asyncio.Event()
    service.env = MagicMock()
    service.logger = MagicMock()
    service.staticdata = None
    service.timestamp_health = None
    service.config = None
    # Initialize MQTT attributes
    service.mqtt_params = MagicMock()
    service.mqtt_client = None
    service.mqtt_message_store = {}
    service._mqtt_loop_running = False
    service._last_message_received = None
    service._mqtt_connected = False
    service._mqtt_connection_event = MagicMock()
    # Initialize FIWARE attributes
    service.fiware_params = MagicMock()
    service.cb_client = MagicMock()
    # Initialize FILE attributes
    service.file_params = MagicMock()
    return service


def create_service_for_config_tests():
    """
    Helper function to create a ControllerBasicService instance for testing
    _load_config and related methods.
    
    Returns:
        ControllerBasicService: Partially initialized service instance with config support.
    """
    service = ControllerBasicService.__new__(ControllerBasicService)
    service.shutdown_event = asyncio.Event()
    service.env = BasicEnvVariables(config_path="test.json")
    service.logger = MagicMock()
    service.staticdata = None
    service.timestamp_health = None
    service.config = None
    # Initialize MQTT attributes
    service.mqtt_params = MagicMock()
    service.mqtt_client = None
    # Initialize FIWARE attributes
    service.fiware_params = MagicMock()
    service.cb_client = MagicMock()
    # Initialize FILE attributes
    service.file_params = MagicMock()
    return service


# Global fixture to prevent ControllerBasicService.__init__ from calling prepare_basic_start
# This allows tests to create service instances without requiring a valid config file
# Tests that need to test prepare_basic_start itself should use create_service_without_init()
@pytest.fixture(scope="session", autouse=True)
def patch_prepare_basic_start():
    """
    Session-wide auto-used fixture that patches ControllerBasicService.prepare_basic_start
    to prevent it from trying to load configuration from a file that doesn't exist in tests.
    
    This fixture allows all tests to create service instances and manually
    configure them as needed without the automatic initialization failing.
    
    Tests that need to test prepare_basic_start itself should create the service
    using create_service_without_init() and then call prepare_basic_start manually.
    """
    # Patch at the class level so all instances use the patched version
    with patch.object(ControllerBasicService, 'prepare_basic_start', lambda self: None):
        yield


@pytest.fixture
def mock_basic_env():
    """
    Fixture providing a mock BasicEnvVariables instance with default test values.
    
    Returns:
        BasicEnvVariables: Configured environment variables for testing.
    """
    return BasicEnvVariables(
        config_path="tests/fixtures/test_config.json",
        log_level="DEBUG",
        log_path="/tmp/encodapy_test",
        log_retention=7,
        log_rotation="1 day",
        reload_staticdata=False,
        start_hold_time=0,
    )


@pytest.fixture
def mock_fiware_entity():
    """
    Fixture providing a mock FIWARE entity configuration.
    
    Returns:
        OutputModel: Configured FIWARE output entity.
    """
    return OutputModel(
        id="fiware_entity_1",
        interface=Interfaces.FIWARE,
        id_interface="fiware_entity_1",
        attributes=[
            AttributeModel(
                id="temperature",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER,
            ),
            AttributeModel(
                id="status",
                type=AttributeTypes.VALUE,
                datatype=DataType.TEXT,
            )
        ],
        commands=[
            CommandModel(id="reset", value=None)
        ]
    )


@pytest.fixture
def mock_file_entity():
    """
    Fixture providing a mock FILE entity configuration.
    
    Returns:
        OutputModel: Configured FILE output entity.
    """
    return OutputModel(
        id="file_entity_1",
        interface=Interfaces.FILE,
        id_interface="file_entity_1",
        attributes=[
            AttributeModel(
                id="pressure",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER,
            )
        ]
    )


@pytest.fixture
def mock_mqtt_entity():
    """
    Fixture providing a mock MQTT entity configuration.
    
    Returns:
        OutputModel: Configured MQTT output entity.
    """
    return OutputModel(
        id="mqtt_entity_1",
        interface=Interfaces.MQTT,
        id_interface="mqtt_entity_1",
        attributes=[
            AttributeModel(
                id="humidity",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER,
            )
        ]
    )


@pytest.fixture
def mock_static_data_entity():
    """
    Fixture providing a mock static data entity configuration.
    
    Returns:
        StaticDataModel: Configured static data entity.
    """
    return StaticDataModel(
        id="static_calibration",
        interface=Interfaces.FIWARE,
        id_interface="calibration_entity",
        attributes=[
            AttributeModel(
                id="calibration_factor",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER
            )
        ]
    )


@pytest.fixture
def mock_input_entity_fiware():
    """
    Fixture providing a mock input entity with FIWARE interface.
    
    Returns:
        InputModel: Configured input entity with FIWARE interface.
    """
    return InputModel(
        id="input_fiware_1",
        interface=Interfaces.FIWARE,
        id_interface="input_fiware_1",
        attributes=[
            AttributeModel(
                id="input_attr",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER
            )
        ]
    )


@pytest.fixture
def mock_input_entity_file():
    """
    Fixture providing a mock input entity with FILE interface.
    
    Returns:
        InputModel: Configured input entity with FILE interface.
    """
    return InputModel(
        id="input_file_1",
        interface=Interfaces.FILE,
        id_interface="input_file_1",
        attributes=[
            AttributeModel(
                id="input_attr",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER
            )
        ]
    )


@pytest.fixture
def mock_input_entity_mqtt():
    """
    Fixture providing a mock input entity with MQTT interface.
    
    Returns:
        InputModel: Configured input entity with MQTT interface.
    """
    return InputModel(
        id="input_mqtt_1",
        interface=Interfaces.MQTT,
        id_interface="input_mqtt_1",
        attributes=[
            AttributeModel(
                id="input_attr",
                type=AttributeTypes.VALUE,
                datatype=DataType.NUMBER
            )
        ]
    )


@pytest.fixture
def mock_config_all_interfaces(
    mock_fiware_entity,
    mock_file_entity,
    mock_mqtt_entity,
    mock_static_data_entity,
    mock_input_entity_fiware,
    mock_input_entity_file,
    mock_input_entity_mqtt
):
    """
    Fixture providing a complete ConfigModel with all interfaces enabled.
    
    Args:
        mock_fiware_entity: Injected FIWARE output entity.
        mock_file_entity: Injected FILE output entity.
        mock_mqtt_entity: Injected MQTT output entity.
        mock_static_data_entity: Injected static data entity.
        mock_input_entity_fiware: Injected FIWARE input entity.
        mock_input_entity_file: Injected FILE input entity.
        mock_input_entity_mqtt: Injected MQTT input entity.
        
    Returns:
        ConfigModel: Complete configuration with all interfaces.
    """
    return ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=True, mqtt=True),
        inputs=[
            mock_input_entity_fiware,
            mock_input_entity_file,
            mock_input_entity_mqtt
        ],
        outputs=[
            mock_fiware_entity,
            mock_file_entity,
            mock_mqtt_entity
        ],
        staticdata=[mock_static_data_entity],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=5.0,
                    timerange_unit=TimeUnits.MINUTE,
                    sampling_time=5,
                    sampling_time_unit=TimeUnits.MINUTE
                ),
                results=TimeSettingsResultsModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                )
            ),
            specific_settings={}
        ),
        controller_components=[]
    )


@pytest.fixture
def mock_config_no_interfaces():
    """
    Fixture providing a ConfigModel with only FIWARE interface enabled.
    
    Note: ConfigModel requires at least one interface to be active,
    so this fixture sets FIWARE to True as minimum.
    
    Returns:
        ConfigModel: Configuration with minimal interfaces (FIWARE only).
    """
    return ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=False, mqtt=False),
        inputs=[],
        outputs=[],
        staticdata=[],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=5.0,
                    timerange_unit=TimeUnits.MINUTE,
                    sampling_time=5,
                    sampling_time_unit=TimeUnits.MINUTE
                ),
                results=TimeSettingsResultsModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                )
            ),
            specific_settings={}
        ),
        controller_components=[]
    )


@pytest.fixture
def mock_config_only_fiware(
    mock_fiware_entity,
    mock_input_entity_fiware
):
    """
    Fixture providing a ConfigModel with only FIWARE interface enabled.
    
    Args:
        mock_fiware_entity: Injected FIWARE output entity.
        mock_input_entity_fiware: Injected FIWARE input entity.
        
    Returns:
        ConfigModel: Configuration with only FIWARE active.
    """
    return ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=False, mqtt=False),
        inputs=[mock_input_entity_fiware],
        outputs=[mock_fiware_entity],
        staticdata=[],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=5.0,
                    timerange_unit=TimeUnits.MINUTE,
                    sampling_time=5,
                    sampling_time_unit=TimeUnits.MINUTE
                ),
                results=TimeSettingsResultsModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                )
            ),
            specific_settings={}
        ),
        controller_components=[]
    )


@pytest.fixture
def basic_service():
    """
    Fixture providing a ControllerBasicService instance with minimal configuration.
    
    This is the legacy fixture from the original test file, kept for compatibility.
    
    Returns:
        ControllerBasicService: Service instance with basic configuration.
    """
    # Use create_service_without_init to avoid calling prepare_basic_start
    service = create_service_without_init()
    service.config = ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=False, mqtt=False),
        inputs=[],
        outputs=[],
        staticdata=[],
        controller_settings=ControllerSettingModel(
            time_settings=TimeSettingsModel(
                calculation=TimeSettingsCalculationModel(
                    timerange=1.0,
                    timerange_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.SECOND
                ),
                calibration=None,
                results=None
            ),
            specific_settings={}
        ),
        controller_components=[],
    )
    service.env = BasicEnvVariables(
        config_path="",
        log_level="DEBUG",
        log_path="",
        log_retention=7,
        log_rotation="1 day",
        reload_staticdata=False,
        start_hold_time=0,
    )
    return service


@pytest.fixture
def service_with_full_config(mock_config_all_interfaces, mock_basic_env):
    """
    Fixture providing a fully configured ControllerBasicService instance.
    
    Args:
        mock_config_all_interfaces: Injected complete configuration.
        mock_basic_env: Injected environment variables.
        
    Returns:
        ControllerBasicService: Service with full configuration.
    """
    service = create_service_without_init()
    service.config = mock_config_all_interfaces
    service.env = mock_basic_env
    return service


@pytest.fixture
def service_with_no_config():
    """
    Fixture providing a ControllerBasicService instance with no configuration.
    
    Returns:
        ControllerBasicService: Service with None configuration.
    """
    # Create service without calling prepare_basic_start
    service = ControllerBasicService.__new__(ControllerBasicService)
    service.shutdown_event = asyncio.Event()
    service.env = MagicMock()
    service.logger = MagicMock()
    service.staticdata = None
    service.timestamp_health = None
    service.config = None
    # Don't call __init__ to avoid prepare_basic_start
    return service


@pytest.fixture
def mock_data_transfer_model():
    """
    Fixture providing a mock DataTransferModel for testing.
    
    Returns:
        DataTransferModel: Model with test components.
    """
    return DataTransferModel(
        components=[
            DataTransferComponentModel(
                entity_id="test_entity",
                attribute_id="test_attr_1",
                value=42.5,
                unit=None,
                timestamp=datetime.now()
            ),
            DataTransferComponentModel(
                entity_id="test_entity",
                attribute_id="test_attr_2",
                value="active",
                unit=None,
                timestamp=datetime.now()
            ),
            DataTransferComponentModel(
                entity_id="test_entity_2",
                attribute_id="test_attr_3",
                value=True,
                unit=None,
                timestamp=datetime.now()
            )
        ]
    )


@pytest.fixture
def mock_output_data_model():
    """
    Fixture providing a mock OutputDataModel for testing.
    
    Returns:
        OutputDataModel: Model with test entities.
    """
    return OutputDataModel(
        entities=[
            OutputDataEntityModel(
                id="test_entity",
                attributes=[
                    AttributeModel(
                        id="attr_1",
                        type=AttributeTypes.VALUE,
                        value=42.5,
                        unit=DataUnits.DEGREECELSIUS,
                        timestamp=datetime.now(),
                        datatype=DataType.NUMBER
                    )
                ],
                commands=[
                    CommandModel(id="cmd_1", value="reset")
                ]
            )
        ]
    )


@pytest.fixture
def mock_input_data_model():
    """
    Fixture providing a mock InputDataModel for testing.
    
    Returns:
        InputDataModel: Model with empty entities (standard for many tests).
    """
    return InputDataModel(
        input_entities=[],
        output_entities=[],
        static_entities=[]
    )


@pytest.fixture
def shutdown_event():
    """
    Fixture providing a pre-set shutdown event for testing service loops.
    
    Returns:
        asyncio.Event: Event that is already set to trigger shutdown.
    """
    event = asyncio.Event()
    event.set()
    return event


@pytest.fixture
def unset_shutdown_event():
    """
    Fixture providing an unset shutdown event for testing service loops.
    
    Returns:
        asyncio.Event: Event that is not set.
    """
    return asyncio.Event()
