"""
Pytest fixtures for component tests.

This module provides common fixtures used across all test files for the
encodapy.components modules.
"""
# pylint: disable=redefined-outer-name

import logging
import sys
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import patch

import loguru
import pytest

from encodapy.components.basic_component import BasicComponent
from encodapy.components.basic_component_config import (
    ConfigDataPoints,
    ControllerComponentModel,
    IOAllocationModel,
    IOModell,
    InputData,
    OutputData,
    ComponentIOModel,
)
from encodapy.utils.datapoints import DataPointGeneral
from encodapy.utils.models import (
    InputDataModel,
    InputDataEntityModel,
    InputDataAttributeModel,
    StaticDataEntityModel,
    AttributeTypes,
)
from encodapy.utils.units import DataUnits


# Reduce log level for cleaner test output
# Suppress DEBUG and INFO logs during test execution
@pytest.fixture(autouse=True, scope="session")
def suppress_debug_logs():
    """Suppress DEBUG and INFO level logs during test execution."""
    # For loguru: remove default handler and add one with WARNING level
    # loguru stores handlers internally, we need to rebuild them
    loguru.logger.remove()  # Remove default handler
    loguru.logger.add(sys.stderr, level="WARNING", format="{message}")

    # Suppress standard logging below WARNING level
    logging.getLogger().setLevel(logging.WARNING)

    yield

    # Reset to default (loguru will recreate default handler on next import)
    loguru.logger.remove()
    loguru.logger.add(
        sys.stderr,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}"
    )
    logging.getLogger().setLevel(logging.NOTSET)


@pytest.fixture
def mock_io_allocation():
    """Fixture providing a mock IOAllocationModel."""
    return IOAllocationModel(
        entity="test_entity",
        attribute="test_attribute"
    )


@pytest.fixture
def mock_io_model():
    """Fixture providing a mock IOModell."""
    return IOModell({
        "input1": IOAllocationModel(entity="entity1", attribute="attr1"),
        "input2": IOAllocationModel(entity="entity2", attribute="attr2"),
    })


@pytest.fixture
def mock_config_data_points():
    """Fixture providing a mock ConfigDataPoints."""
    return ConfigDataPoints({
        "param1": IOAllocationModel(entity="static_entity", attribute="param1"),
        "param2": DataPointGeneral(value=42.0, unit=DataUnits.DEGREECELSIUS),
    })


@pytest.fixture
def mock_controller_component_config():
    """Fixture providing a mock ControllerComponentModel."""
    return ControllerComponentModel(
        id="test_component",
        type="test_type",
        active=True,
        inputs=IOModell({
            "input1": IOAllocationModel(entity="input_entity", attribute="input_attr"),
        }),
        outputs=IOModell({
            "output1": IOAllocationModel(entity="output_entity", attribute="output_attr"),
        }),
        config=ConfigDataPoints({
            "static_param": IOAllocationModel(entity="static_entity", attribute="static_attr"),
        })
    )


@pytest.fixture
def mock_component_io_model():
    """Fixture providing a mock ComponentIOModel."""
    # Create a simple ComponentIOModel for testing
    class MockInputData(InputData):
        """Mock input data for testing."""
        input1: Optional[None] = None

    class MockOutputData(OutputData):
        """Mock output data for testing."""
        output1: Optional[None] = None

    return ComponentIOModel(
        input=MockInputData(),
        output=MockOutputData()
    )


@pytest.fixture
def mock_data_point():
    """Fixture providing a mock DataPointGeneral."""
    return DataPointGeneral(
        value=25.5,
        unit=DataUnits.DEGREECELSIUS,
        time=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_input_data_entity():
    """Fixture providing a mock InputDataEntityModel."""
    return InputDataEntityModel(
        id="input_entity",
        attributes=[
            InputDataAttributeModel(
                id="input_attr",
                data=25.5,
                unit=DataUnits.DEGREECELSIUS,
                latest_timestamp_input=datetime.now(timezone.utc),
                data_available=True,
                data_type=AttributeTypes.VALUE
            )
        ]
    )


@pytest.fixture
def mock_static_data_entity():
    """Fixture providing a mock StaticDataEntityModel."""
    return StaticDataEntityModel(
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


@pytest.fixture
def mock_input_data_model(mock_input_data_entity, mock_static_data_entity):
    """Fixture providing a mock InputDataModel."""
    return InputDataModel(
        input_entities=[mock_input_data_entity],
        output_entities=[],
        static_entities=[mock_static_data_entity]
    )


@pytest.fixture
def mock_basic_component(mock_controller_component_config):
    """Fixture providing a BasicComponent instance for testing."""
    # We need to mock the component loading and model validation
    with patch.object(
        BasicComponent, '_get_input_and_output_config_models',
        return_value=(InputData, OutputData)
    ):
        component = BasicComponent.__new__(BasicComponent)
        component.component_config = mock_controller_component_config
        component.io_model = None
        component.config_data = None
        component.input_data = None
        component.output_data = None
        return component


@pytest.fixture
def mock_component_config_without_io():
    """Fixture providing a ControllerComponentModel without inputs/outputs for testing."""
    return ControllerComponentModel(
        id="test_component_no_io",
        type="test_type_no_io",
        active=True,
        inputs=IOModell({}),
        outputs=IOModell({}),
        config=None
    )
