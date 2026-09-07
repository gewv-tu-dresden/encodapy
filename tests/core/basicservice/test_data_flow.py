"""
Tests for ControllerBasicService data flow processing.

This module contains tests for data retrieval, output preparation, and output
mapping functionality of the ControllerBasicService class.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import (
    DataQueryTypes,
    Interfaces,
    OutputModel,
    AttributeModel,
    AttributeTypes,
    CommandModel,
    InputModel,
)
from encodapy.utils.models import (
    InputDataModel,
    OutputDataModel,
    OutputDataEntityModel,
    DataTransferModel,
    DataTransferComponentModel,
)
from encodapy.utils.units import DataUnits
from filip.models.base import DataType


class TestGetData:
    """Test class for the get_data method."""

    @pytest.mark.asyncio
    async def test_get_data(self, basic_service):
        """
        Test the get_data method with all three interfaces (FIWARE, FILE, MQTT).
        
        Verifies that get_data correctly calls the appropriate data retrieval methods
        for each interface type and returns an InputDataModel with the expected
        number of input and output entities.
        """
        from encodapy.utils.models import OutputDataEntityModel
        
        basic_service.config.inputs = [
            InputModel(id="input_1", interface=Interfaces.FIWARE, id_interface="input_1", attributes=[], commands=[]),
            InputModel(id="input_2", interface=Interfaces.FILE, id_interface="input_2", attributes=[], commands=[]),
            InputModel(id="input_3", interface=Interfaces.MQTT, id_interface="input_3", attributes=[], commands=[]),
        ]
        basic_service.config.outputs = [
            OutputModel(id="output_1", interface=Interfaces.FIWARE, id_interface="output_1", attributes=[], commands=[]),
            OutputModel(id="output_2", interface=Interfaces.FILE, id_interface="output_2", attributes=[], commands=[]),
            OutputModel(id="output_3", interface=Interfaces.MQTT, id_interface="output_3", attributes=[], commands=[]),
        ]
        
        with patch.object(basic_service, 'get_data_from_fiware') as mock_get_data_fiware, \
             patch.object(basic_service, 'get_data_from_file') as mock_get_data_file, \
             patch.object(basic_service, 'get_data_from_mqtt') as mock_get_data_mqtt, \
             patch.object(basic_service, '_get_last_timestamp_for_fiware_output') as mock_get_last_timestamp_fiware, \
             patch.object(basic_service, '_get_last_timestamp_for_file_output') as mock_get_last_timestamp_file, \
             patch.object(basic_service, '_get_last_timestamp_for_mqtt_output') as mock_get_last_timestamp_mqtt:
            
            # Return InputDataEntityModel objects for all interfaces
            # Note: FIWARE and FILE check for None before appending, but MQTT does not
            # So we return empty lists to avoid validation errors
            from encodapy.utils.models import InputDataEntityModel
            mock_get_data_fiware.return_value = InputDataEntityModel(id="input_1", attributes=[])
            mock_get_data_file.return_value = InputDataEntityModel(id="input_2", attributes=[])
            mock_get_data_mqtt.return_value = InputDataEntityModel(id="input_3", attributes=[])
            
            # Return OutputDataEntityModel objects for timestamps (not None)
            mock_get_last_timestamp_fiware.return_value = (OutputDataEntityModel(id="output_1", attributes=[], commands=[]), None)
            mock_get_last_timestamp_file.return_value = (OutputDataEntityModel(id="output_2", attributes=[], commands=[]), None)
            mock_get_last_timestamp_mqtt.return_value = (OutputDataEntityModel(id="output_3", attributes=[], commands=[]), None)
            
            result = await basic_service.get_data(method=DataQueryTypes.CALCULATION)
            
            assert isinstance(result, InputDataModel)
            # All interfaces return valid entities
            assert len(result.input_entities) == 3
            # output_entities contains the OutputDataEntityModel from _get_last_timestamp_* calls
            assert len(result.output_entities) == 3
            
            mock_get_data_fiware.assert_called_once()
            mock_get_data_file.assert_called_once()
            mock_get_data_mqtt.assert_called_once()
            mock_get_last_timestamp_fiware.assert_called_once()
            mock_get_last_timestamp_file.assert_called_once()
            mock_get_last_timestamp_mqtt.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_no_config(self, service_with_no_config):
        """
        Test get_data when service has no configuration.
        
        Verifies that get_data returns an empty InputDataModel when
        the service configuration is None.
        """
        service_with_no_config.config = None
        
        result = await service_with_no_config.get_data(method=DataQueryTypes.CALCULATION)
        
        assert isinstance(result, InputDataModel)
        assert len(result.input_entities) == 0
        assert len(result.output_entities) == 0
        assert len(result.static_entities) == 0

    @pytest.mark.asyncio
    async def test_get_data_empty_config(self, basic_service):
        """
        Test get_data with empty configuration (no inputs or outputs).
        
        Verifies that get_data handles empty configuration gracefully.
        """
        basic_service.config.inputs = []
        basic_service.config.outputs = []
        
        result = await basic_service.get_data(method=DataQueryTypes.CALCULATION)
        
        assert isinstance(result, InputDataModel)
        assert len(result.input_entities) == 0
        assert len(result.output_entities) == 0

    @pytest.mark.asyncio
    async def test_get_data_all_interfaces_return_none(self, basic_service):
        """
        Test get_data when all interface methods return None.
        
        Verifies that get_data handles the case where all data retrieval
        methods return None.
        """
        from encodapy.utils.models import OutputDataEntityModel
        
        basic_service.config.inputs = [
            InputModel(id="input_1", interface=Interfaces.FIWARE, id_interface="input_1", attributes=[], commands=[]),
            InputModel(id="input_2", interface=Interfaces.FILE, id_interface="input_2", attributes=[], commands=[]),
        ]
        basic_service.config.outputs = [
            OutputModel(id="output_1", interface=Interfaces.FIWARE, id_interface="output_1", attributes=[], commands=[]),
            OutputModel(id="output_2", interface=Interfaces.FILE, id_interface="output_2", attributes=[], commands=[]),
        ]
        
        with patch.object(basic_service, 'get_data_from_fiware', return_value=None), \
             patch.object(basic_service, 'get_data_from_file', return_value=None), \
             patch.object(basic_service, 'get_data_from_mqtt', return_value=None), \
             patch.object(basic_service, '_get_last_timestamp_for_fiware_output', return_value=(OutputDataEntityModel(id="output_1", attributes=[], commands=[]), None)), \
             patch.object(basic_service, '_get_last_timestamp_for_file_output', return_value=(OutputDataEntityModel(id="output_2", attributes=[], commands=[]), None)), \
             patch.object(basic_service, '_get_last_timestamp_for_mqtt_output', return_value=(OutputDataEntityModel(id="output_3", attributes=[], commands=[]), None)):
            
            result = await basic_service.get_data(method=DataQueryTypes.CALCULATION)
        
        assert isinstance(result, InputDataModel)
        # All return None, so input_entities should be empty
        assert len(result.input_entities) == 0

    @pytest.mark.asyncio
    async def test_get_data_reload_staticdata_disabled(self, basic_service):
        """
        Test get_data when reload_staticdata is disabled.
        
        Verifies that static data is not reloaded when the environment
        variable reload_staticdata is False.
        """
        basic_service.config.inputs = []
        basic_service.config.outputs = []
        basic_service.env.reload_staticdata = False
        basic_service.staticdata = []
        
        with patch.object(basic_service, 'reload_static_data') as mock_reload:
            result = await basic_service.get_data(method=DataQueryTypes.CALCULATION)
        
        # reload_static_data should not be called
        mock_reload.assert_not_called()
        # Should use existing staticdata
        assert len(result.static_entities) == 0

    @pytest.mark.asyncio
    async def test_get_data_reload_staticdata_enabled(self, basic_service):
        """
        Test get_data when reload_staticdata is enabled.
        
        Verifies that static data is reloaded when the environment
        variable reload_staticdata is True.
        """
        basic_service.config.inputs = []
        basic_service.config.outputs = []
        basic_service.env.reload_staticdata = True
        basic_service.staticdata = None
        
        with patch.object(basic_service, 'reload_static_data', return_value=[]) as mock_reload:
            result = await basic_service.get_data(method=DataQueryTypes.CALCULATION)
        
        # reload_static_data should be called
        mock_reload.assert_called_once()


class TestSendOutputs:
    """Test class for the send_outputs method."""

    @pytest.mark.asyncio
    async def test_send_outputs(self, basic_service):
        """
        Test the send_outputs method with FIWARE interface.
        
        Verifies that send_outputs correctly processes output data for FIWARE
        entities, including attributes and commands, and calls the appropriate
        sending method.
        """
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            id_interface="test_entity",
            attributes=[
                AttributeModel(id="test_attr", type=AttributeTypes.VALUE, datatype=DataType.TEXT),
            ],
            commands=[
                CommandModel(id="test_command", value=None),
            ],
        )
        
        output_data = OutputDataModel(
            entities=[
                OutputDataEntityModel(
                    id="test_entity",
                    attributes=[
                        AttributeModel(
                            id="test_attr",
                            type=AttributeTypes.VALUE,
                            value="test_value",
                            unit=DataUnits.WTT,
                            timestamp=datetime.now(),
                            datatype=DataType.TEXT,
                        ),
                    ],
                    commands=[
                        CommandModel(
                            id="test_command",
                            value="test_value",
                        ),
                    ],
                ),
            ],
        )
        
        basic_service.config.outputs = [output_entity]
        
        with patch.object(basic_service, '_get_output_entity_config') as mock_get_entity_config, \
             patch.object(basic_service, '_get_output_attribute_config') as mock_get_attr_config, \
             patch.object(basic_service, '_get_output_command_config') as mock_get_command_config, \
             patch.object(basic_service, '_send_data_to_fiware') as mock_send_fiware:
            
            mock_get_entity_config.return_value = output_entity
            mock_get_attr_config.return_value = output_entity.attributes[0]
            mock_get_command_config.return_value = output_entity.commands[0]
            mock_send_fiware.return_value = AsyncMock()
            
            await basic_service.send_outputs(data_output=output_data)
            
            mock_get_entity_config.assert_called_once()
            mock_get_attr_config.assert_called_once()
            mock_get_command_config.assert_called_once()
            mock_send_fiware.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_outputs_none_data(self, basic_service):
        """
        Test send_outputs with None data output.
        
        Verifies that send_outputs handles None input gracefully
        and does not attempt to send any data.
        """
        basic_service.config = MagicMock()
        basic_service.config.outputs = []
        
        await basic_service.send_outputs(data_output=None)
        
        # Should complete without errors

    @pytest.mark.asyncio
    async def test_send_outputs_empty_entities(self, basic_service):
        """
        Test send_outputs with empty entities list.
        
        Verifies that send_outputs handles an OutputDataModel with
        no entities gracefully.
        """
        output_data = OutputDataModel(entities=[])
        basic_service.config = MagicMock()
        basic_service.config.outputs = []
        
        await basic_service.send_outputs(data_output=output_data)
        
        # Should complete without errors

    @pytest.mark.asyncio
    async def test_send_outputs_no_matching_entity_config(self, basic_service):
        """
        Test send_outputs when output entity has no matching config.
        
        Verifies that send_outputs skips entities that don't have a
        matching configuration.
        """
        output_data = OutputDataModel(
            entities=[
                OutputDataEntityModel(
                    id="nonexistent_entity",
                    attributes=[],
                    commands=[]
                )
            ]
        )
        basic_service.config = MagicMock()
        basic_service.config.outputs = [
            OutputModel(id="existing_entity", interface=Interfaces.FIWARE, id_interface="existing_entity", attributes=[], commands=[])
        ]
        
        with patch.object(basic_service, '_get_output_entity_config', return_value=None) as mock_get_config:
            # Patch logger at the module level where it's used
            with patch('encodapy.service.basic_service.logger') as mock_logger:
                await basic_service.send_outputs(data_output=output_data)
            
            # Should log debug message about entity not found
            mock_logger.debug.assert_called()
            # Check all debug calls for the message
            found = False
            for call in mock_logger.debug.call_args_list:
                if "not found in configuration" in str(call):
                    found = True
                    break
            assert found, "Expected 'not found in configuration' in debug log"

    @pytest.mark.asyncio
    async def test_send_outputs_no_attributes_or_commands(self, basic_service):
        """
        Test send_outputs when entity has no attributes or commands.
        
        Verifies that send_outputs skips entities that have no
        attributes or commands to send.
        """
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            id_interface="test_entity",
            attributes=[],
            commands=[]
        )
        basic_service.config = MagicMock()
        basic_service.config.outputs = [output_entity]
        
        output_data = OutputDataModel(
            entities=[
                OutputDataEntityModel(
                    id="test_entity",
                    attributes=[],
                    commands=[]
                )
            ]
        )
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            await basic_service.send_outputs(data_output=output_data)
        
        # Should log debug message about skipping
        mock_logger.debug.assert_called()
        # Check the debug calls for skip message
        skip_found = False
        for call in mock_logger.debug.call_args_list:
            if "Skip sending" in str(call):
                skip_found = True
                break
        assert skip_found, "Expected 'Skip sending' in debug log calls"


class TestPrepareOutput:
    """Test class for the prepare_output method."""

    def test_prepare_output(self, basic_service):
        """
        Test the prepare_output method.
        
        Verifies that prepare_output correctly transforms a DataTransferModel
        into an OutputDataModel with the expected structure, including entities
        with attributes.
        """
        data_output = DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id="test_entity",
                    attribute_id="test_attr",
                    value="test_value",
                    unit=DataUnits.WTT,
                    timestamp=datetime.now(),
                ),
            ],
        )
        
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            id_interface="test_entity",
            attributes=[
                AttributeModel(id="test_attr", type=AttributeTypes.VALUE, datatype=DataType.TEXT),
            ],
            commands=[]
        )
        
        basic_service.config.outputs = [output_entity]
        
        result = basic_service.prepare_output(data_output=data_output)
        
        assert isinstance(result, OutputDataModel)
        assert len(result.entities) == 1
        assert result.entities[0].id == "test_entity"
        assert len(result.entities[0].attributes) == 1
        assert result.entities[0].attributes[0].id == "test_attr"
        assert result.entities[0].attributes[0].value == "test_value"

    def test_prepare_output_none_data(self, basic_service):
        """
        Test prepare_output with None data output.
        
        Verifies that prepare_output returns an empty OutputDataModel
        when the input DataTransferModel is None.
        """
        basic_service.config = MagicMock()
        basic_service.config.outputs = []
        
        result = basic_service.prepare_output(data_output=None)
        
        assert isinstance(result, OutputDataModel)
        assert len(result.entities) == 0

    def test_prepare_output_no_config(self, basic_service):
        """
        Test prepare_output when service has no configuration.
        
        Verifies that prepare_output handles the case when the service
        configuration is None.
        """
        basic_service.config = None
        
        data_output = DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id="test",
                    attribute_id="attr",
                    value=1,
                    unit=DataUnits.WTT,
                    timestamp=datetime.now()
                )
            ]
        )
        
        with patch('encodapy.service.basic_service.logger') as mock_logger:
            result = basic_service.prepare_output(data_output=data_output)
        
        assert isinstance(result, OutputDataModel)
        assert len(result.entities) == 0
        # Should log error about missing configuration
        mock_logger.error.assert_called()

    def test_prepare_output_empty_data_output(self, basic_service):
        """
        Test prepare_output with empty DataTransferModel.
        
        Verifies that prepare_output handles an empty DataTransferModel
        (no components) correctly.
        """
        basic_service.config = MagicMock()
        basic_service.config.outputs = [
            OutputModel(id="test_entity", interface=Interfaces.FIWARE, id_interface="test_entity", attributes=[], commands=[])
        ]
        
        data_output = DataTransferModel(components=[])
        
        result = basic_service.prepare_output(data_output=data_output)
        
        assert isinstance(result, OutputDataModel)
        # Should create entities for all configured outputs, but with empty attributes
        assert len(result.entities) == 1
        assert result.entities[0].id == "test_entity"
        assert len(result.entities[0].attributes) == 0
        assert len(result.entities[0].commands) == 0

    def test_prepare_output_component_no_matching_entity(self, basic_service):
        """
        Test prepare_output when component has no matching output entity.
        
        Verifies that prepare_output skips components that don't have
        a matching output entity in the configuration.
        """
        basic_service.config = MagicMock()
        basic_service.config.outputs = [
            OutputModel(id="other_entity", interface=Interfaces.FIWARE, id_interface="other_entity", attributes=[], commands=[])
        ]
        
        data_output = DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id="nonexistent_entity",
                    attribute_id="attr",
                    value=1,
                    unit=DataUnits.WTT,
                    timestamp=datetime.now()
                )
            ]
        )
        
        result = basic_service.prepare_output(data_output=data_output)
        
        assert isinstance(result, OutputDataModel)
        # Should still create entity for configured output, but without the component data
        assert len(result.entities) == 1
        assert result.entities[0].id == "other_entity"
        assert len(result.entities[0].attributes) == 0

    def test_prepare_output_multiple_components_same_entity(self, basic_service):
        """
        Test prepare_output with multiple components for the same entity.
        
        Verifies that prepare_output correctly processes multiple
        components that belong to the same output entity.
        """
        basic_service.config = MagicMock()
        basic_service.config.outputs = [
            OutputModel(
                id="test_entity",
                interface=Interfaces.FIWARE,
                id_interface="test_entity",
                attributes=[
                    AttributeModel(id="attr_1", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
                    AttributeModel(id="attr_2", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
                ],
                commands=[]
            )
        ]
        
        data_output = DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id="test_entity",
                    attribute_id="attr_1",
                    value=1.0,
                    unit=DataUnits.WTT,
                    timestamp=datetime.now()
                ),
                DataTransferComponentModel(
                    entity_id="test_entity",
                    attribute_id="attr_2",
                    value=2.0,
                    unit=DataUnits.KWT,
                    timestamp=datetime.now()
                )
            ]
        )
        
        result = basic_service.prepare_output(data_output=data_output)
        
        assert len(result.entities) == 1
        assert result.entities[0].id == "test_entity"
        assert len(result.entities[0].attributes) == 2


class TestGetOutputEntityConfig:
    """Test class for the _get_output_entity_config method."""

    def test_get_output_entity_config_found(self, service_with_no_config):
        """
        Test finding an output entity by ID.
        
        Verifies that the method correctly returns the OutputModel when
        an entity with the specified ID exists in the configuration.
        """
        service_with_no_config.config = MagicMock()
        
        # Create output entities
        entity_1 = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[],
            commands=[]
        )
        entity_2 = OutputModel(
            id="entity_2",
            interface=Interfaces.FILE,
            id_interface="entity_2",
            attributes=[],
            commands=[]
        )
        
        service_with_no_config.config.outputs = [entity_1, entity_2]
        
        result = service_with_no_config._get_output_entity_config("entity_1")
        
        assert result is entity_1
        assert result.id == "entity_1"

    def test_get_output_entity_config_not_found(self, service_with_no_config):
        """
        Test not finding an output entity by ID.
        
        Verifies that the method returns None when no entity with the
        specified ID exists in the configuration.
        """
        service_with_no_config.config = MagicMock()
        service_with_no_config.config.outputs = [
            OutputModel(id="entity_1", interface=Interfaces.FIWARE, id_interface="entity_1", attributes=[], commands=[])
        ]
        
        result = service_with_no_config._get_output_entity_config("nonexistent")
        
        assert result is None

    def test_get_output_entity_config_empty_outputs(self, service_with_no_config):
        """
        Test getting entity config with empty outputs list.
        
        Verifies that the method returns None when the outputs list
        is empty.
        """
        service_with_no_config.config = MagicMock()
        service_with_no_config.config.outputs = []
        
        result = service_with_no_config._get_output_entity_config("any_id")
        
        assert result is None

    def test_get_output_entity_config_no_config(self, service_with_no_config):
        """
        Test getting entity config with no configuration.
        
        Verifies that the method returns None when the service has no
        configuration loaded.
        """
        service_with_no_config.config = None
        
        result = service_with_no_config._get_output_entity_config("any_id")
        
        assert result is None

    def test_get_output_entity_config_multiple_entities(self, service_with_no_config):
        """
        Test finding entity among multiple entities with similar IDs.
        
        Verifies that the method correctly identifies the exact matching
        entity even when there are multiple entities with similar IDs.
        """
        service_with_no_config.config = MagicMock()
        
        # Create output entities with similar IDs
        entities = [
            OutputModel(id="entity_1", interface=Interfaces.FIWARE, id_interface="entity_1", attributes=[], commands=[]),
            OutputModel(id="entity_2", interface=Interfaces.FIWARE, id_interface="entity_2", attributes=[], commands=[]),
            OutputModel(id="entity_1_backup", interface=Interfaces.FIWARE, id_interface="entity_1_backup", attributes=[], commands=[]),
            OutputModel(id="entity_1", interface=Interfaces.FILE, id_interface="entity_1", attributes=[], commands=[]),  # Same ID, different interface
        ]
        
        service_with_no_config.config.outputs = entities
        
        result = service_with_no_config._get_output_entity_config("entity_1")
        
        # Should return the first matching entity
        assert result is not None
        assert result.id == "entity_1"


class TestGetOutputAttributeConfig:
    """Test class for the _get_output_attribute_config method."""

    def test_get_output_attribute_config_found(self, service_with_no_config):
        """
        Test finding an output attribute by entity ID and attribute ID.
        
        Verifies that the method correctly returns the AttributeModel when
        an attribute with the specified IDs exists in the configuration.
        """
        service_with_no_config.config = MagicMock()
        
        # Create output entity with attributes
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[
                AttributeModel(id="temp", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
                AttributeModel(id="humidity", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
            ],
            commands=[]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_attribute_config("entity_1", "temp")
        
        assert result is not None
        assert result.id == "temp"

    def test_get_output_attribute_config_not_found_entity(self, service_with_no_config):
        """
        Test not finding attribute when entity does not exist.
        
        Verifies that the method returns None when the specified entity
        does not exist in the configuration.
        """
        service_with_no_config.config = MagicMock()
        
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[
                AttributeModel(id="temp", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
            ],
            commands=[]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_attribute_config("nonexistent_entity", "temp")
        
        assert result is None

    def test_get_output_attribute_config_not_found_attribute(self, service_with_no_config):
        """
        Test not finding attribute when it does not exist in entity.
        
        Verifies that the method returns None when the specified attribute
        does not exist in the specified entity.
        """
        service_with_no_config.config = MagicMock()
        
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[
                AttributeModel(id="temp", type=AttributeTypes.VALUE, datatype=DataType.NUMBER),
            ],
            commands=[]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_attribute_config("entity_1", "nonexistent_attr")
        
        assert result is None


class TestGetOutputCommandConfig:
    """Test class for the _get_output_command_config method."""

    def test_get_output_command_config_found(self, service_with_no_config):
        """
        Test finding an output command by entity ID and command ID.
        
        Verifies that the method correctly returns the CommandModel when
        a command with the specified IDs exists in the configuration.
        """
        service_with_no_config.config = MagicMock()
        
        # Create output entity with commands
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[],
            commands=[
                CommandModel(id="reset", value=None),
                CommandModel(id="start", value=None),
            ]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_command_config("entity_1", "reset")
        
        assert result is not None
        assert result.id == "reset"

    def test_get_output_command_config_not_found_entity(self, service_with_no_config):
        """
        Test not finding command when entity does not exist.
        
        Verifies that the method returns None when the specified entity
        does not exist in the configuration.
        """
        service_with_no_config.config = MagicMock()
        
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[],
            commands=[
                CommandModel(id="reset", value=None),
            ]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_command_config("nonexistent_entity", "reset")
        
        assert result is None

    def test_get_output_command_config_not_found_command(self, service_with_no_config):
        """
        Test not finding command when it does not exist in entity.
        
        Verifies that the method returns None when the specified command
        does not exist in the specified entity.
        """
        service_with_no_config.config = MagicMock()
        
        entity = OutputModel(
            id="entity_1",
            interface=Interfaces.FIWARE,
            id_interface="entity_1",
            attributes=[],
            commands=[
                CommandModel(id="reset", value=None),
            ]
        )
        
        service_with_no_config.config.outputs = [entity]
        
        result = service_with_no_config._get_output_command_config("entity_1", "nonexistent_cmd")
        
        assert result is None
