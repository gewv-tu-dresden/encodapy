"""
Tests for ControllerBasicService configuration loading and management.

This module contains tests for the _load_config method and related
configuration functionality of the ControllerBasicService class.
"""

from unittest.mock import patch, MagicMock

import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import ConfigModel, BasicEnvVariables
from encodapy.utils.error_handling import ConfigError, InterfaceNotActive
from pydantic import ValidationError


class TestLoadConfig:
    """Test class for the _load_config method."""

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_success(
        self, 
        mock_from_json,
        mock_config_all_interfaces
    ):
        """
        Test successful configuration loading.
        
        Verifies that _load_config successfully loads and assigns the
        configuration from the specified file path.
        """
        import asyncio
        
        mock_from_json.return_value = mock_config_all_interfaces
        
        # Create service without __init__ to avoid prepare_basic_start
        service = ControllerBasicService.__new__(ControllerBasicService)
        service.shutdown_event = asyncio.Event()
        service.env = BasicEnvVariables(config_path="tests/fixtures/test_config.json")
        service.config = None
        # Initialize interface load methods as mocks
        service.load_fiware_params = MagicMock()
        service.load_file_params = MagicMock()
        service.load_mqtt_params = MagicMock()
        
        service._load_config()
        
        assert service.config is not None
        assert isinstance(service.config, ConfigModel)
        mock_from_json.assert_called_once_with(file_path="tests/fixtures/test_config.json")

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_fiware_interface_enabled(
        self, 
        mock_from_json,
        mock_config_only_fiware
    ):
        """
        Test that FIWARE interface preparation is called when enabled in config.
        
        Verifies that load_fiware_params is called when the FIWARE interface
        is enabled in the loaded configuration.
        """
        import asyncio
        
        mock_from_json.return_value = mock_config_only_fiware
        
        # Create service without __init__ to avoid prepare_basic_start
        service = ControllerBasicService.__new__(ControllerBasicService)
        service.shutdown_event = asyncio.Event()
        service.env = BasicEnvVariables(config_path="test.json")
        service.config = None
        
        with patch.object(service, 'load_fiware_params') as mock_load_fiware, \
             patch.object(service, 'load_file_params') as mock_load_file, \
             patch.object(service, 'load_mqtt_params') as mock_load_mqtt:
            service._load_config()
            mock_load_fiware.assert_called_once()
            mock_load_file.assert_not_called()
            mock_load_mqtt.assert_not_called()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_file_interface_enabled(
        self, 
        mock_from_json,
        mock_config_all_interfaces,
        service_with_no_config
    ):
        """
        Test that FILE interface preparation is called when enabled in config.
        
        Verifies that load_file_params is called when the FILE interface
        is enabled in the loaded configuration.
        """
        mock_from_json.return_value = mock_config_all_interfaces
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params') as mock_load_fiware, \
             patch.object(service_with_no_config, 'load_file_params') as mock_load_file, \
             patch.object(service_with_no_config, 'load_mqtt_params') as mock_load_mqtt:
            service_with_no_config._load_config()
            mock_load_file.assert_called_once()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_mqtt_interface_enabled(
        self, 
        mock_from_json,
        mock_config_all_interfaces,
        service_with_no_config
    ):
        """
        Test that MQTT interface preparation is called when enabled in config.
        
        Verifies that load_mqtt_params is called when the MQTT interface
        is enabled in the loaded configuration.
        """
        mock_from_json.return_value = mock_config_all_interfaces
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params') as mock_load_fiware, \
             patch.object(service_with_no_config, 'load_file_params') as mock_load_file, \
             patch.object(service_with_no_config, 'load_mqtt_params') as mock_load_mqtt:
            service_with_no_config._load_config()
            mock_load_mqtt.assert_called_once()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    @patch('encodapy.service.basic_service.logger')
    def test_load_config_file_not_found_error(
        self, 
        mock_logger, 
        mock_from_json,
        service_with_no_config
    ):
        """
        Test error handling when configuration file is not found.
        
        Verifies that the service exits with code 1 when the configuration
        file does not exist, and logs the error appropriately.
        """
        mock_from_json.side_effect = FileNotFoundError("Config file not found")
        service_with_no_config.env = BasicEnvVariables(config_path="nonexistent.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params'):
            with pytest.raises(SystemExit) as exc_info:
                service_with_no_config._load_config()
            
            assert exc_info.value.code == 1
            mock_logger.error.assert_called_once()
            assert "Error loading configuration file" in str(mock_logger.error.call_args)

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    @patch('encodapy.service.basic_service.logger')
    def test_load_config_validation_error(
        self, 
        mock_logger, 
        mock_from_json,
        service_with_no_config
    ):
        """
        Test error handling when configuration file has validation errors.
        
        Verifies that the service exits with code 1 when the configuration
        file contains invalid data that fails Pydantic validation.
        """
        # Create a real ValidationError by triggering Pydantic validation
        from pydantic import BaseModel, Field
        
        class TestModel(BaseModel):
            required_field: str = Field(..., description="Required")
        
        try:
            TestModel(required_field=None)
        except Exception as e:
            validation_error = e
        
        mock_from_json.side_effect = validation_error
        service_with_no_config.env = BasicEnvVariables(config_path="invalid.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params'):
            with pytest.raises(SystemExit) as exc_info:
                service_with_no_config._load_config()
            
            assert exc_info.value.code == 1
            mock_logger.error.assert_called_once()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    @patch('encodapy.service.basic_service.logger')
    def test_load_config_config_error(
        self, 
        mock_logger, 
        mock_from_json,
        service_with_no_config
    ):
        """
        Test error handling for ConfigError during configuration loading.
        
        Verifies that the service exits with code 1 when a ConfigError
        occurs during configuration loading.
        """
        mock_from_json.side_effect = ConfigError("Configuration error")
        service_with_no_config.env = BasicEnvVariables(config_path="error.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params'):
            with pytest.raises(SystemExit) as exc_info:
                service_with_no_config._load_config()
            
            assert exc_info.value.code == 1
            mock_logger.error.assert_called_once()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    @patch('encodapy.service.basic_service.logger')
    def test_load_config_interface_not_active_error(
        self, 
        mock_logger, 
        mock_from_json,
        service_with_no_config
    ):
        """
        Test error handling when an interface is not active.
        
        Verifies that the service exits with code 1 when an InterfaceNotActive
        error occurs during configuration loading.
        """
        mock_from_json.side_effect = InterfaceNotActive("Interface not active")
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params'):
            with pytest.raises(SystemExit) as exc_info:
                service_with_no_config._load_config()
            
            assert exc_info.value.code == 1
            mock_logger.error.assert_called_once()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    @patch('encodapy.service.basic_service.logger')
    def test_load_config_debug_log_on_success(
        self, 
        mock_logger, 
        mock_from_json,
        mock_config_all_interfaces,
        service_with_no_config
    ):
        """
        Test that a debug message is logged on successful configuration loading.
        
        Verifies that the service logs a debug message when the configuration
        is successfully loaded.
        """
        mock_from_json.return_value = mock_config_all_interfaces
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params'), \
             patch.object(service_with_no_config, 'load_file_params'), \
             patch.object(service_with_no_config, 'load_mqtt_params'):
            service_with_no_config._load_config()
        
        mock_logger.debug.assert_called_once()
        assert "Config succesfully loaded" in str(mock_logger.debug.call_args)


class TestLoadConfigInterfaces:
    """Test class for interface-specific configuration loading."""

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_all_interfaces_disabled(
        self, 
        mock_from_json,
        mock_config_no_interfaces,
        service_with_no_config
    ):
        """
        Test that no interface preparation is called when all interfaces are disabled.
        
        Note: ConfigModel requires at least one interface to be active,
        so mock_config_no_interfaces has FIWARE enabled as minimum.
        This test verifies that when no additional interfaces are enabled,
        only the minimum required interface preparation is called.
        """
        mock_from_json.return_value = mock_config_no_interfaces
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params') as mock_fiware, \
             patch.object(service_with_no_config, 'load_file_params') as mock_file, \
             patch.object(service_with_no_config, 'load_mqtt_params') as mock_mqtt:
            
            service_with_no_config._load_config()
            
            # mock_config_no_interfaces has fiware=True as minimum
            mock_fiware.assert_called_once()
            mock_file.assert_not_called()
            mock_mqtt.assert_not_called()

    @patch('encodapy.service.basic_service.ConfigModel.from_json')
    def test_load_config_only_fiware_enabled(
        self, 
        mock_from_json,
        mock_config_only_fiware,
        service_with_no_config
    ):
        """
        Test that only FIWARE interface preparation is called when only FIWARE is enabled.
        
        Verifies that only the FIWARE interface preparation method is called
        when the configuration has only FIWARE enabled.
        """
        mock_from_json.return_value = mock_config_only_fiware
        service_with_no_config.env = BasicEnvVariables(config_path="test.json")
        
        with patch.object(service_with_no_config, 'load_fiware_params') as mock_fiware, \
             patch.object(service_with_no_config, 'load_file_params') as mock_file, \
             patch.object(service_with_no_config, 'load_mqtt_params') as mock_mqtt:
            
            service_with_no_config._load_config()
            
            mock_fiware.assert_called_once()
            mock_file.assert_not_called()
            mock_mqtt.assert_not_called()
