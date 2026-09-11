"""
Tests for ControllerBasicService static data loading and management.

This module contains tests for the reload_static_data method and related
static data functionality of the ControllerBasicService class.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import DataQueryTypes, Interfaces, StaticDataModel, AttributeTypes, AttributeModel, DataType
from encodapy.utils.models import StaticDataEntityModel, InputDataAttributeModel


class TestReloadStaticData:
    """Test class for the reload_static_data method."""

    def test_reload_static_data_empty_config(self, service_with_full_config):
        """
        Test that empty static data configuration returns empty list.
        
        Verifies that reload_static_data returns an empty list when the
        configuration has no static data entities defined.
        """
        service_with_full_config.config.staticdata = []
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        assert result == []

    def test_reload_static_data_returns_list(self, service_with_full_config):
        """
        Test that reload_static_data always returns a list.
        
        Verifies that the return value is always a list, even when no
        static data is configured.
        """
        service_with_full_config.config.staticdata = []
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        assert isinstance(result, list)

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_fiware_interface(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test static data loading via FIWARE interface.
        
        Verifies that static data is correctly loaded from FIWARE when
        the static data entity has FIWARE interface configured.
        """
        # Configure the service with a FIWARE static data entity
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        
        # Mock the FIWARE data retrieval to return a StaticDataEntityModel
        mock_fiware_data = StaticDataEntityModel(
            id='static_calibration',
            attributes=[
                InputDataAttributeModel(
                    id='calibration_factor',
                    data=0.95,
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_fiware.return_value = mock_fiware_data
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        assert len(result) == 1
        assert isinstance(result[0], StaticDataEntityModel)
        mock_get_data_fiware.assert_called_once()

    @patch.object(ControllerBasicService, 'get_staticdata_from_file')
    def test_reload_static_data_file_interface(
        self, 
        mock_get_data_file,
        service_with_full_config
    ):
        """
        Test static data loading via FILE interface.
        
        Verifies that static data is correctly loaded from FILE when
        the static data entity has FILE interface configured.
        """
        # Create a FILE static data entity
        file_static_entity = StaticDataModel(
            id="file_static",
            interface=Interfaces.FILE,
            id_interface="file_entity",
            attributes=[
                AttributeModel(
                    id="file_attr",
                    type=AttributeTypes.VALUE,
                    datatype=DataType.NUMBER
                )
            ]
        )
        service_with_full_config.config.staticdata = [file_static_entity]
        
        # Mock the FILE data retrieval
        mock_file_data = StaticDataEntityModel(
            id="file_static",
            attributes=[
                InputDataAttributeModel(
                    id="file_attr",
                    data=[1, 2, 3],
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_file.return_value = mock_file_data
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALIBRATION,
            staticdata=[]
        )
        
        assert len(result) == 1
        assert isinstance(result[0], StaticDataEntityModel)
        mock_get_data_file.assert_called_once()

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    @patch.object(ControllerBasicService, 'get_staticdata_from_file')
    def test_reload_static_data_mixed_interfaces(
        self, 
        mock_get_data_file,
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test static data loading with multiple interfaces.
        
        Verifies that static data is correctly loaded from multiple
        interfaces when they are all configured.
        """
        # Add both FIWARE and FILE static data entities
        file_static_entity = StaticDataModel(
            id="file_static",
            interface=Interfaces.FILE,
            id_interface="file_entity",
            attributes=[
                AttributeModel(
                    id="file_attr",
                    type=AttributeTypes.VALUE,
                    datatype=DataType.NUMBER
                )
            ]
        )
        service_with_full_config.config.staticdata = [
            mock_static_data_entity,
            file_static_entity
        ]
        
        # Mock both data sources
        mock_fiware_data = StaticDataEntityModel(
            id='static_calibration',
            attributes=[
                InputDataAttributeModel(
                    id='calibration_factor',
                    data=0.95,
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_fiware.return_value = mock_fiware_data
        
        mock_file_data = StaticDataEntityModel(
            id="file_static",
            attributes=[
                InputDataAttributeModel(
                    id="file_attr",
                    data=[1, 2, 3],
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_file.return_value = mock_file_data
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        assert len(result) == 2
        assert all(isinstance(item, StaticDataEntityModel) for item in result)
        mock_get_data_fiware.assert_called_once()
        mock_get_data_file.assert_called_once()

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_fiware_returns_none(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test static data loading when FIWARE returns None.
        
        Verifies that static data loading handles the case when the
        FIWARE interface returns None (no data available).
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        mock_get_data_fiware.return_value = None
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        assert result == []

    def test_reload_static_data_mqtt_warning(self, service_with_full_config):
        """
        Test that MQTT interface for static data logs a warning.
        
        Verifies that the service logs a warning when a static data entity
        is configured with MQTT interface, which is not supported.
        """
        mqtt_static_entity = StaticDataModel(
            id="mqtt_static",
            interface=Interfaces.MQTT,
            id_interface="mqtt_entity",
            attributes=[
                AttributeModel(
                    id="mqtt_attr",
                    type=AttributeTypes.VALUE,
                    datatype=DataType.NUMBER
                )
            ]
        )
        service_with_full_config.config.staticdata = [mqtt_static_entity]
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            result = service_with_full_config.reload_static_data(
                method=DataQueryTypes.CALCULATION,
                staticdata=[]
            )
        
        mock_logger.warning.assert_called()
        calls_str = str([call for call in mock_logger.warning.call_args_list])
        assert "interface MQTT for staticdata not supported" in calls_str
        assert result == []  # MQTT static data is not loaded

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_appends_to_existing(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test that new static data is appended to existing list.
        
        Verifies that reload_static_data appends new data to the existing
        staticdata list instead of replacing it.
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        
        # Mock the FIWARE data retrieval to return a proper StaticDataEntityModel
        mock_fiware_data = StaticDataEntityModel(
            id='static_calibration',
            attributes=[
                InputDataAttributeModel(
                    id='calibration_factor',
                    data=0.95,
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_fiware.return_value = mock_fiware_data
        
        # Start with some existing data
        existing_data = [
            StaticDataEntityModel(
                id="existing",
                attributes=[
                    InputDataAttributeModel(
                        id="existing_attr",
                        data=1.0,
                        unit=None,
                        data_type=AttributeTypes.VALUE,
                        data_available=True,
                        latest_timestamp_input=datetime.now()
                    )
                ]
            )
        ]
        
        result = service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=existing_data
        )
        
        assert len(result) == 2  # Existing + new
        assert result[0].id == "existing"
        assert result[1].id == "static_calibration"

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_calibration_method(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test static data loading with CALIBRATION method.
        
        Verifies that the method parameter is correctly passed to the
        interface data retrieval methods.
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        
        # Mock the FIWARE data retrieval to return a proper StaticDataEntityModel
        mock_fiware_data = StaticDataEntityModel(
            id='static_calibration',
            attributes=[
                InputDataAttributeModel(
                    id='calibration_factor',
                    data=0.95,
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_fiware.return_value = mock_fiware_data
        
        service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALIBRATION,
            staticdata=[]
        )
        
        # Verify that get_data_from_fiware was called with CALIBRATION method
        mock_get_data_fiware.assert_called_once()
        call_args = mock_get_data_fiware.call_args
        assert call_args[1]['method'] == DataQueryTypes.CALIBRATION

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_timestamp_parameter(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test that timestamp_latest_output parameter is correctly passed.
        
        Verifies that the timestamp_latest_output parameter (None for static data)
        is correctly passed to the interface data retrieval methods.
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        
        # Mock the FIWARE data retrieval to return a proper StaticDataEntityModel
        mock_fiware_data = StaticDataEntityModel(
            id='static_calibration',
            attributes=[
                InputDataAttributeModel(
                    id='calibration_factor',
                    data=0.95,
                    unit=None,
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=datetime.now()
                )
            ]
        )
        mock_get_data_fiware.return_value = mock_fiware_data
        
        service_with_full_config.reload_static_data(
            method=DataQueryTypes.CALCULATION,
            staticdata=[]
        )
        
        # Verify that timestamp_latest_output is None for static data
        call_args = mock_get_data_fiware.call_args
        assert call_args[1]['timestamp_latest_output'] is None


class TestReloadStaticDataErrorHandling:
    """Test class for error handling in reload_static_data."""

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_key_error(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test error handling for KeyError during static data loading.
        
        Verifies that KeyError during static data loading does not crash
        the service (error is caught and logged).
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        mock_get_data_fiware.side_effect = KeyError("missing_key")
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            result = service_with_full_config.reload_static_data(
                method=DataQueryTypes.CALCULATION,
                staticdata=[]
            )
        
        # Should still return list with the existing data (empty list in this case)
        assert isinstance(result, list)
        # Error should be logged
        mock_logger.error.assert_called()
        calls_str = str([call for call in mock_logger.error.call_args_list])
        assert "missing_key" in calls_str or "Error loading static data" in calls_str

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_value_error(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test error handling for ValueError during static data loading.
        
        Verifies that ValueError during static data loading does not crash
        the service (error is caught and logged).
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        mock_get_data_fiware.side_effect = ValueError("invalid_value")
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            result = service_with_full_config.reload_static_data(
                method=DataQueryTypes.CALCULATION,
                staticdata=[]
            )
        
        # Should still return list (may contain data from other entities)
        assert isinstance(result, list)
        # Error should be logged
        mock_logger.error.assert_called()
        calls_str = str([call for call in mock_logger.error.call_args_list])
        assert "invalid_value" in calls_str or "Error loading static data" in calls_str

    @patch.object(ControllerBasicService, 'get_data_from_fiware')
    def test_reload_static_data_type_error(
        self, 
        mock_get_data_fiware,
        mock_static_data_entity,
        service_with_full_config
    ):
        """
        Test error handling for TypeError during static data loading.
        
        Verifies that TypeError during static data loading does not crash
        the service (error is caught and logged).
        """
        service_with_full_config.config.staticdata = [mock_static_data_entity]
        mock_get_data_fiware.side_effect = TypeError("type_error")
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            result = service_with_full_config.reload_static_data(
                method=DataQueryTypes.CALCULATION,
                staticdata=[]
            )
        
        # Should still return list (may contain data from other entities)
        assert isinstance(result, list)
        # Error should be logged
        mock_logger.error.assert_called()
        calls_str = str([call for call in mock_logger.error.call_args_list])
        assert "type_error" in calls_str or "Error loading static data" in calls_str
