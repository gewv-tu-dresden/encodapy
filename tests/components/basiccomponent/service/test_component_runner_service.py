"""
Unit tests for encodapy.service.component_runner_service module.

Tests the ComponentRunnerService class and its methods.
"""
# pylint: disable=protected-access
import asyncio
from datetime import datetime, timezone
from typing import Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from encodapy.components.basic_component import BasicComponent
from encodapy.components.basic_component_config import (
    ControllerComponentModel,
    IOModell,
    IOAllocationModel,
    ConfigDataPoints,
    DataPointGeneral,
)
from encodapy.service.component_runner_service import ComponentRunnerService
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataModel,
    InputDataEntityModel,
    InputDataAttributeModel,
    StaticDataEntityModel,
    AttributeTypes,
)
from encodapy.utils.units import DataUnits


class MockComponent(BasicComponent):
    """Mock component for testing ComponentRunnerService."""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        self.component_config = config if isinstance(config, ControllerComponentModel) \
            else config[0]
        self.config_data = None
        self.io_model = MagicMock()
        self.input_data = None
        self.output_data = MagicMock()

        # Mock the io_model to have the expected structure
        self.io_model.output = MagicMock()
        self.io_model.output.model_dump.return_value = {
            "output_attr": IOAllocationModel(entity="output_entity", attribute="output_attr")
        }

        # Mock output_data to have expected attributes
        self.output_data.state_of_charge = DataPointGeneral(value=80.0, unit=DataUnits.PERCENT)
        self.output_data.temperature = DataPointGeneral(value=25.0, unit=DataUnits.DEGREECELSIUS)

    def run(self, data):
        """Mock run method that returns test results."""
        return [
            DataTransferComponentModel(
                entity_id="output_entity",
                attribute_id="output_attr",
                value=42.0,
                unit=DataUnits.DEGREECELSIUS,
                timestamp=datetime.now(timezone.utc)
            )
        ]

    def calibrate(self, static_data=None):
        """Mock calibrate method — intentionally a no-op for testing."""


class TestComponentRunnerServiceInit:
    """Tests for ComponentRunnerService.__init__ method."""

    def test_init_without_shutdown_event(self):
        """Test initializing ComponentRunnerService without shutdown_event."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()
        assert not service.components

    def test_init_with_shutdown_event(self):
        """Test initializing ComponentRunnerService with shutdown_event."""
        shutdown_event = asyncio.Event()
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService(shutdown_event=shutdown_event)
        assert not service.components


class TestComponentRunnerServicePrepareStart:
    """Tests for ComponentRunnerService.prepare_start method."""

    def test_prepare_start_no_components(self):
        """Test prepare_start when there are no components in config."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        # Mock the config to have empty controller_components
        service.config = MagicMock()
        service.config.controller_components = []
        service.staticdata = []
        service.env = MagicMock()

        service.prepare_start()

        assert not service.components

    def test_prepare_start_with_components(self):
        """Test prepare_start when there are components in config."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        # Create mock components config
        component_configs = [
            ControllerComponentModel(
                id="component_1",
                type="test_type",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({}),
            ),
            ControllerComponentModel(
                id="component_2",
                type="test_type",
                active=False,  # This one should be skipped
                inputs=IOModell({}),
                outputs=IOModell({}),
            ),
            ControllerComponentModel(
                id="component_3",
                type="test_type",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({}),
            ),
        ]

        service.config = MagicMock()
        service.config.controller_components = component_configs
        service.staticdata = []
        service.env = MagicMock()

        with patch(
            'encodapy.service.component_runner_service.get_component_class_model'
        ) as mock_get_class:
            mock_get_class.return_value = MockComponent

            service.prepare_start()

            # Should only have 2 components (active ones)
            assert len(service.components) == 2
            assert service.components[0].component_config.id == "component_1"
            assert service.components[1].component_config.id == "component_3"

    def test_prepare_start_with_static_data(self):
        """Test prepare_start with static data for components."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        component_configs = [
            ControllerComponentModel(
                id="component_1",
                type="test_type",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({}),
                config=ConfigDataPoints({
                    "param1": IOAllocationModel(entity="static_entity", attribute="param1")
                })
            ),
        ]

        service.config = MagicMock()
        service.config.controller_components = component_configs
        service.staticdata = [
            StaticDataEntityModel(
                id="static_entity",
                attributes=[
                    InputDataAttributeModel(
                        id="param1",
                        data=100.0,
                        unit=DataUnits.LITER,
                        latest_timestamp_input=datetime.now(timezone.utc),
                        data_available=True,
                        data_type=AttributeTypes.VALUE
                    )
                ]
            )
        ]
        service.env = MagicMock()

        with patch(
            'encodapy.service.component_runner_service.get_component_class_model'
        ) as mock_get_class:
            mock_get_class.return_value = MockComponent

            service.prepare_start()

            assert len(service.components) == 1


class TestComponentRunnerServiceHelperMethods:
    """Tests for ComponentRunnerService helper methods."""

    def test_result_to_input_data_attribute(self):
        """Test _result_to_input_data_attribute method."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        result = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="test_attr",
            value=42.0,
            unit=DataUnits.DEGREECELSIUS,
            timestamp=datetime.now(timezone.utc)
        )

        attribute = service._result_to_input_data_attribute(result)

        assert attribute.id == "test_attr"
        assert attribute.data == 42.0
        assert attribute.unit == DataUnits.DEGREECELSIUS
        assert attribute.latest_timestamp_input == result.timestamp
        assert attribute.data_available is True

    def test_add_result_to_input_entity_existing_attribute(self):
        """Test _add_result_to_input_entity when attribute already exists."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        result = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="existing_attr",
            value=50.0,
            unit=DataUnits.PERCENT,
            timestamp=datetime.now(timezone.utc)
        )

        input_entity = InputDataEntityModel(
            id="test_entity",
            attributes=[
                InputDataAttributeModel(
                    id="existing_attr",
                    data=25.0,
                    unit=DataUnits.PERCENT,
                    latest_timestamp_input=datetime.now(timezone.utc),
                    data_available=True,
                    data_type=AttributeTypes.VALUE
                )
            ]
        )

        updated_entity = service._add_result_to_input_entity(result, input_entity)

        # Should update the existing attribute
        assert len(updated_entity.attributes) == 1
        assert updated_entity.attributes[0].data == 50.0
        assert updated_entity.attributes[0].unit == DataUnits.PERCENT

    def test_add_result_to_input_entity_new_attribute(self):
        """Test _add_result_to_input_entity when attribute doesn't exist."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        result = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="new_attr",
            value=75.0,
            unit=DataUnits.DEGREECELSIUS,
            timestamp=datetime.now(timezone.utc)
        )

        input_entity = InputDataEntityModel(
            id="test_entity",
            attributes=[
                InputDataAttributeModel(
                    id="existing_attr",
                    data=25.0,
                    unit=DataUnits.PERCENT,
                    latest_timestamp_input=datetime.now(timezone.utc),
                    data_available=True,
                    data_type=AttributeTypes.VALUE
                )
            ]
        )

        updated_entity = service._add_result_to_input_entity(result, input_entity)

        # Should add a new attribute
        assert len(updated_entity.attributes) == 2
        new_attr = next(attr for attr in updated_entity.attributes if attr.id == "new_attr")
        assert new_attr.data == 75.0
        assert new_attr.unit == DataUnits.DEGREECELSIUS


class TestComponentRunnerServiceAddResultsToInput:
    """Tests for ComponentRunnerService.add_results_to_input method."""

    def test_add_results_to_input_existing_entity(self):
        """Test add_results_to_input when entity already exists."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        result = DataTransferComponentModel(
            entity_id="existing_entity",
            attribute_id="new_attr",
            value=100.0,
            unit=DataUnits.WTT,
            timestamp=datetime.now(timezone.utc)
        )

        input_data = InputDataModel(
            input_entities=[
                InputDataEntityModel(
                    id="existing_entity",
                    attributes=[
                        InputDataAttributeModel(
                            id="existing_attr",
                            data=50.0,
                            unit=DataUnits.PERCENT,
                            latest_timestamp_input=datetime.now(timezone.utc),
                            data_available=True,
                            data_type=AttributeTypes.VALUE
                        )
                    ]
                )
            ],
            output_entities=[],
            static_entities=[]
        )

        updated_data = service.add_results_to_input(input_data, [result])

        # Should add new attribute to existing entity
        assert len(updated_data.input_entities) == 1
        assert len(updated_data.input_entities[0].attributes) == 2

    def test_add_results_to_input_new_entity(self):
        """Test add_results_to_input when entity doesn't exist."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        result = DataTransferComponentModel(
            entity_id="new_entity",
            attribute_id="new_attr",
            value=200.0,
            unit=DataUnits.WTT,
            timestamp=datetime.now(timezone.utc)
        )

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        updated_data = service.add_results_to_input(input_data, [result])

        # Should add new entity
        assert len(updated_data.input_entities) == 1
        assert updated_data.input_entities[0].id == "new_entity"
        assert len(updated_data.input_entities[0].attributes) == 1
        assert updated_data.input_entities[0].attributes[0].id == "new_attr"

    def test_add_results_to_input_multiple_results(self):
        """Test add_results_to_input with multiple results."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        results = [
            DataTransferComponentModel(
                entity_id="entity_1",
                attribute_id="attr_1",
                value=100.0,
                unit=DataUnits.WTT,
                timestamp=datetime.now(timezone.utc)
            ),
            DataTransferComponentModel(
                entity_id="entity_2",
                attribute_id="attr_2",
                value=200.0,
                unit=DataUnits.VLT,
                timestamp=datetime.now(timezone.utc)
            ),
        ]

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        updated_data = service.add_results_to_input(input_data, results)

        # Should add both entities
        assert len(updated_data.input_entities) == 2


class TestComponentRunnerServiceCalculation:
    """Tests for ComponentRunnerService.calculation method."""

    @pytest.mark.asyncio
    async def test_calculation_success(self):
        """Test calculation method with successful component execution."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        # Create mock components
        mock_component_1 = MockComponent(
            config=ControllerComponentModel(
                id="component_1",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="component_1"
        )

        mock_component_2 = MockComponent(
            config=ControllerComponentModel(
                id="component_2",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="component_2"
        )

        service.components = [mock_component_1, mock_component_2]
        service.env = MagicMock()
        service.env.reload_staticdata = False

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        result = await service.calculation(input_data)

        assert isinstance(result, DataTransferModel)
        assert len(result.components) == 2  # 2 components * 1 result each (from MockComponent.run)

    @pytest.mark.asyncio
    async def test_calculation_with_component_error(self):
        """Test calculation method when a component raises an error."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        # Create a mock component that raises an error
        class FailingComponent(BasicComponent):  # pylint: disable=super-init-not-called
            """Component stub that always raises during run()."""

            def __init__(  # pylint: disable=super-init-not-called
                self,
                config: Union[ControllerComponentModel, list[ControllerComponentModel]],
                component_id: str,
                static_data: Optional[list[StaticDataEntityModel]] = None,
            ) -> None:
                self.component_config = config if isinstance(config, ControllerComponentModel) \
                    else config[0]

            def run(self, data):
                """Raise an error to simulate a failing component."""
                raise ValueError("Test component error")

        mock_component = FailingComponent(
            config=ControllerComponentModel(
                id="failing_component",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="failing_component"
        )

        service.components = [mock_component]
        service.env = MagicMock()
        service.env.reload_staticdata = False

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        result = await service.calculation(input_data)

        # Should still return DataTransferModel, but with no components
        assert isinstance(result, DataTransferModel)
        assert len(result.components) == 0

    @pytest.mark.asyncio
    async def test_calculation_results_added_to_input(self):
        """Test that calculation adds results to input for subsequent components."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        mock_component_1 = MockComponent(
            config=ControllerComponentModel(
                id="component_1",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="component_1"
        )

        mock_component_2 = MockComponent(
            config=ControllerComponentModel(
                id="component_2",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="component_2"
        )

        service.components = [mock_component_1, mock_component_2]
        service.env = MagicMock()
        service.env.reload_staticdata = False

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        result = await service.calculation(input_data)

        # The calculation should have added results from component_1 to the input
        # before running component_2
        assert isinstance(result, DataTransferModel)


class TestComponentRunnerServiceCalibration:
    """Tests for ComponentRunnerService.calibration method."""

    @pytest.mark.asyncio
    async def test_calibration_success(self):
        """Test calibration method with successful execution."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        mock_component = MockComponent(
            config=ControllerComponentModel(
                id="test_component",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="test_component"
        )

        # Mock the calibrate method to verify it's called
        mock_component.calibrate = MagicMock()

        service.components = [mock_component]
        service.env = MagicMock()
        service.env.reload_staticdata = True

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[
                StaticDataEntityModel(
                    id="static_entity",
                    attributes=[
                        InputDataAttributeModel(
                            id="static_attr",
                            data=100.0,
                            unit=DataUnits.LITER,
                            latest_timestamp_input=datetime.now(timezone.utc),
                            data_available=True,
                            data_type=AttributeTypes.VALUE
                        )
                    ]
                )
            ]
        )

        await service.calibration(input_data)

        # Verify calibrate was called with static data
        mock_component.calibrate.assert_called_once()

    @pytest.mark.asyncio
    async def test_calibration_reload_staticdata_disabled(self):
        """Test calibration when reload_staticdata is disabled."""
        # Mock the service to avoid loading config during init
        with patch.object(ComponentRunnerService, 'prepare_basic_start'):
            service = ComponentRunnerService()

        mock_component = MockComponent(
            config=ControllerComponentModel(
                id="test_component",
                type="test",
                active=True,
                inputs=IOModell({}),
                outputs=IOModell({})
            ),
            component_id="test_component"
        )

        # Mock the calibrate method to verify it's called with None
        mock_component.calibrate = MagicMock()

        service.components = [mock_component]
        service.env = MagicMock()
        service.env.reload_staticdata = False  # Disabled

        input_data = InputDataModel(
            input_entities=[],
            output_entities=[],
            static_entities=[]
        )

        await service.calibration(input_data)

        # Verify calibrate was called with None for static_data
        mock_component.calibrate.assert_called_once_with(static_data=None)
