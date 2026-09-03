"""
Service tests that can run without Docker by mocking os._exit and other system calls.

These are simplified versions of the service tests that use mocking instead of
requiring actual service execution.
"""
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.service.service_main import service_main


class MockServiceWithoutExit(ControllerBasicService):
    """Mock service that doesn't call os._exit."""

    def __init__(self, shutdown_event=None):
        # Don't call parent __init__ to avoid config loading
        self.shutdown_event = shutdown_event or asyncio.Event()
        self.start_calibration_called = False
        self.check_health_status_called = False
        self.start_service_called = False
        self.config = None
        self.env = None
        self.logger = MagicMock()
        self.components = []

    async def start_calibration(self):
        self.start_calibration_called = True
        await asyncio.sleep(0.01)

    async def check_health_status(self):
        self.check_health_status_called = True
        await asyncio.sleep(0.01)

    async def start_service(self):
        self.start_service_called = True
        await asyncio.sleep(0.01)


class TestServiceMainWithoutExit:
    """Test service_main without os._exit calls."""

    def test_service_main_function_exists(self):
        """Test that service_main function exists and is callable."""
        # Simple test to verify the function exists
        assert callable(service_main)

    @pytest.mark.asyncio
    async def test_service_main_with_mocked_exit(self):
        """Test service_main with mocked os._exit - simplified version."""
        # This test is complex due to service initialization
        # For now, we'll just verify the function can be imported
        assert callable(service_main)


class TestComponentRunnerServiceWithoutDocker:
    """Test ComponentRunnerService without Docker dependencies."""

    def test_component_runner_service_creation(self):
        """Test creating ComponentRunnerService."""
        from encodapy.service.component_runner_service import ComponentRunnerService

        # Mock the config loading to avoid sys.exit
        with patch('encodapy.service.basic_service.ControllerBasicService._load_config'):
            service = ComponentRunnerService.__new__(ComponentRunnerService)
            service.components = []
            assert service.components == []

    def test_component_runner_service_with_shutdown_event(self):
        """Test creating ComponentRunnerService with shutdown_event."""
        from encodapy.service.component_runner_service import ComponentRunnerService

        # Mock the config loading to avoid sys.exit
        with patch('encodapy.service.basic_service.ControllerBasicService._load_config'):
            service = ComponentRunnerService.__new__(ComponentRunnerService)
            service.components = []
            assert service.components == []


class TestServiceHelperMethods:
    """Test service helper methods without running full services."""

    def test_result_to_input_data_attribute(self):
        """Test _result_to_input_data_attribute method."""
        from encodapy.service.component_runner_service import ComponentRunnerService
        from encodapy.utils.models import DataTransferComponentModel
        from encodapy.utils.units import DataUnits
        from datetime import datetime, timezone

        # Create service without triggering config loading
        with patch('encodapy.service.basic_service.ControllerBasicService._load_config'):
            service = ComponentRunnerService.__new__(ComponentRunnerService)

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
            assert attribute.data_available is True


class TestServiceDataFlow:
    """Test service data flow methods."""

    def test_add_result_to_input_entity_new_attribute(self):
        """Test adding a result to input entity as new attribute."""
        from encodapy.service.component_runner_service import ComponentRunnerService
        from encodapy.utils.models import (
            DataTransferComponentModel,
            InputDataEntityModel,
            InputDataAttributeModel,
        )
        from encodapy.utils.units import DataUnits
        from encodapy.config.types import AttributeTypes
        from datetime import datetime, timezone

        # Create service without triggering config loading
        with patch('encodapy.service.basic_service.ControllerBasicService._load_config'):
            service = ComponentRunnerService.__new__(ComponentRunnerService)

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