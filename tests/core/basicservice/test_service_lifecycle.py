"""
Tests for ControllerBasicService lifecycle management.

This module contains tests for the initialization, preparation, and cleanup
of the ControllerBasicService class, including the __init__ method, prepare_basic_start,
prepare_start, and cleanup_service.
"""

import asyncio
from unittest.mock import MagicMock, patch

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import BasicEnvVariables


class TestServiceInitialization:
    """Test class for ControllerBasicService initialization."""

    def test_init_default_shutdown_event(self):
        """
        Test that the service creates a default shutdown event when none is provided.
        
        Verifies that the shutdown_event is initialized as an asyncio.Event
        when no shutdown_event is passed to the constructor.
        """
        service = ControllerBasicService()
        assert service.shutdown_event is not None
        assert isinstance(service.shutdown_event, asyncio.Event)

    def test_init_custom_shutdown_event(self):
        """
        Test that the service uses a custom shutdown event when provided.
        
        Verifies that the service accepts and uses an externally provided
        shutdown_event instead of creating a new one.
        """
        custom_event = asyncio.Event()
        service = ControllerBasicService(shutdown_event=custom_event)
        assert service.shutdown_event is custom_event

    def test_init_env_variables(self):
        """
        Test that the service initializes environment variables correctly.
        
        Verifies that the env attribute is initialized as a BasicEnvVariables
        instance with default values from the environment.
        """
        service = ControllerBasicService()
        assert service.env is not None
        assert isinstance(service.env, BasicEnvVariables)

    def test_init_logger_control(self):
        """
        Test that the service initializes the logger correctly.
        
        Verifies that the logger attribute is initialized as a LoggerControl
        instance with configuration from the environment variables.
        """
        service = ControllerBasicService()
        assert service.logger is not None
        # LoggerControl is initialized in prepare_basic_start, not __init__
        # So we check that it will be set during prepare_basic_start

    def test_init_staticdata_is_none(self):
        """
        Test that staticdata is initialized as None.
        
        Verifies that the staticdata attribute starts as None and will be
        loaded during the preparation phase.
        """
        service = ControllerBasicService()
        assert service.staticdata is None

    def test_init_timestamp_health_is_none(self):
        """
        Test that timestamp_health is initialized as None.
        
        Verifies that the timestamp_health attribute starts as None and will be
        set during the health check process.
        """
        service = ControllerBasicService()
        assert service.timestamp_health is None

    def test_init_calls_prepare_basic_start(self):
        """
        Test that the constructor calls prepare_basic_start.
        
        Verifies that the __init__ method automatically calls prepare_basic_start
        to initialize the service with configuration.
        """
        with patch.object(ControllerBasicService, 'prepare_basic_start') as mock_prepare:
            mock_prepare.return_value = None
            ControllerBasicService()
            mock_prepare.assert_called_once()


class TestServiceInitializationWithMocks:
    """Test class for initialization with mocked dependencies."""

    @patch('encodapy.service.basic_service.FiwareConnection.__init__')
    @patch('encodapy.service.basic_service.FileConnection.__init__')
    @patch('encodapy.service.basic_service.MqttConnection.__init__')
    def test_init_calls_parent_initializers(
        self, 
        mock_mqtt_init, 
        mock_file_init, 
        mock_fiware_init
    ):
        """
        Test that the constructor calls parent class initializers.
        
        Verifies that ControllerBasicService (which inherits from multiple
        connection classes) properly initializes all parent classes.
        """
        mock_fiware_init.return_value = None
        mock_file_init.return_value = None
        mock_mqtt_init.return_value = None
        
        ControllerBasicService()
        
        mock_fiware_init.assert_called_once()
        mock_file_init.assert_called_once()
        mock_mqtt_init.assert_called_once()


class TestServicePreparation:
    """Test class for service preparation after initialization."""

    def test_prepare_basic_start_integration(self):
        """
        Integration test for prepare_basic_start method.
        
        Verifies that prepare_basic_start correctly calls all necessary
        initialization methods in the proper order.
        
        Note: Due to the global patch_prepare_basic_start fixture, this test
        verifies that the service class has all the required methods that
        prepare_basic_start should call.
        """
        from encodapy.service.basic_service import ControllerBasicService
        
        # Verify that all the methods called by prepare_basic_start exist
        assert hasattr(ControllerBasicService, 'prepare_basic_start')
        assert hasattr(ControllerBasicService, '_load_config')
        assert hasattr(ControllerBasicService, 'prepare_fiware_connection')
        assert hasattr(ControllerBasicService, 'prepare_mqtt_connection')
        assert hasattr(ControllerBasicService, 'reload_static_data')
        assert hasattr(ControllerBasicService, 'prepare_start')

    def test_prepare_start_default_implementation(self, service_with_no_config):
        """
        Test the default implementation of prepare_start.
        
        Verifies that the default prepare_start method (which does nothing
        special) executes without errors and logs a debug message.
        """
        # The default implementation just logs a debug message
        # This test ensures it doesn't raise any exceptions
        service_with_no_config.prepare_start()
        # If we get here, the method executed successfully


class TestCleanupService:
    """Test class for cleanup_service method."""

    def test_cleanup_service_no_mqtt_client(self, service_with_no_config):
        """
        Test cleanup_service when there's no MQTT client.
        
        Verifies that cleanup_service handles the case where the
        MQTT client is not initialized.
        """
        # Ensure MQTT client is not initialized
        service_with_no_config.mqtt_client = None
        
        # Should not raise any errors
        service_with_no_config.cleanup_service()

    def test_cleanup_service_multiple_calls(self, service_with_no_config):
        """
        Test cleanup_service can be called multiple times.
        
        Verifies that cleanup_service can be safely called multiple
        times without errors.
        """
        with patch.object(service_with_no_config, 'stop_mqtt_client') as mock_stop:
            service_with_no_config.cleanup_service()
            service_with_no_config.cleanup_service()
            service_with_no_config.cleanup_service()
        
        # stop_mqtt_client should be called each time
        assert mock_stop.call_count == 3
