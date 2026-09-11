"""
Unit tests for encodapy.components.basic_component_config module.

Tests the configuration models and data structures used by components.
"""
from typing import Optional
import pytest

from encodapy.components.basic_component_config import (
    ComponentValidationError,
    ConfigData,
    ConfigDataPoints,
    ControllerComponentModel,
    ComponentIOModel,
    InputData,
    OutputData,
    IOAllocationModel,
    IOModell,
    DataPointGeneral,
)
from encodapy.utils.units import DataUnits


class TestIOAllocationModel:
    """Tests for IOAllocationModel class."""

    def test_io_allocation_creation(self):
        """Test creating an IOAllocationModel with valid data."""
        model = IOAllocationModel(
            entity="test_entity",
            attribute="test_attribute"
        )
        assert model.entity == "test_entity"
        assert model.attribute == "test_attribute"

    def test_io_allocation_validation_missing_entity(self):
        """Test that IOAllocationModel raises validation error when entity is missing."""
        with pytest.raises(Exception):  # Should raise validation error
            IOAllocationModel(attribute="test_attribute")

    def test_io_allocation_validation_missing_attribute(self):
        """Test that IOAllocationModel raises validation error when attribute is missing."""
        with pytest.raises(Exception):  # Should raise validation error
            IOAllocationModel(entity="test_entity")


class TestIOModell:
    """Tests for IOModell class."""

    def test_io_model_creation(self):
        """Test creating an IOModell with allocations."""
        allocations = {
            "input1": IOAllocationModel(entity="entity1", attribute="attr1"),
            "input2": IOAllocationModel(entity="entity2", attribute="attr2"),
        }
        model = IOModell(allocations)
        assert len(model.root) == 2
        assert model.root["input1"].entity == "entity1"
        assert model.root["input2"].attribute == "attr2"

    def test_io_model_empty(self):
        """Test creating an empty IOModell."""
        model = IOModell({})
        assert len(model.root) == 0


class TestConfigDataPoints:
    """Tests for ConfigDataPoints class."""

    def test_config_data_points_creation(self):
        """Test creating ConfigDataPoints with mixed types."""
        data = {
            "param1": IOAllocationModel(entity="static_entity", attribute="param1"),
            "param2": DataPointGeneral(value=42.0, unit=DataUnits.DEGREECELSIUS),
        }
        model = ConfigDataPoints(data)
        assert len(model.root) == 2
        assert isinstance(model.root["param1"], IOAllocationModel)
        assert isinstance(model.root["param2"], DataPointGeneral)


class TestControllerComponentModel:
    """Tests for ControllerComponentModel class."""

    def test_controller_component_creation(self):
        """Test creating a ControllerComponentModel with all fields."""
        component = ControllerComponentModel(
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
        assert component.id == "test_component"
        assert component.type == "test_type"
        assert component.active is True
        assert len(component.inputs.root) == 1
        assert len(component.outputs.root) == 1
        assert len(component.config.root) == 1

    def test_controller_component_minimal(self):
        """Test creating a ControllerComponentModel with minimal fields."""
        component = ControllerComponentModel(
            id="minimal_component",
            type="minimal_type",
            inputs=IOModell({}),
            outputs=IOModell({}),
        )
        assert component.id == "minimal_component"
        assert component.type == "minimal_type"
        assert component.active is True  # Default value
        assert len(component.inputs.root) == 0
        assert len(component.outputs.root) == 0

    def test_controller_component_inactive(self):
        """Test creating a ControllerComponentModel that is inactive."""
        component = ControllerComponentModel(
            id="inactive_component",
            type="inactive_type",
            active=False,
            inputs=IOModell({}),
            outputs=IOModell({}),
        )
        assert component.active is False


class TestComponentData:
    """Tests for ComponentData class and its subclasses."""

    def test_input_data_creation(self):
        """Test creating InputData with DataPointGeneral fields."""
        # InputData is a base class, we need to create a subclass
        class TestInputData(InputData):
            temperature: Optional[DataPointGeneral] = None
            pressure: Optional[DataPointGeneral] = None

        data = TestInputData(
            temperature=DataPointGeneral(value=25.0, unit=DataUnits.DEGREECELSIUS),
            pressure=DataPointGeneral(value=1013.0, unit=None)
        )
        assert data.temperature.value == 25.0
        assert data.temperature.unit == DataUnits.DEGREECELSIUS
        assert data.pressure.value == 1013.0
        assert data.pressure.unit is None

    def test_output_data_creation(self):
        """Test creating OutputData with DataPointGeneral fields."""
        class TestOutputData(OutputData):
            state_of_charge: Optional[DataPointGeneral] = None
            status: Optional[DataPointGeneral] = None

        data = TestOutputData(
            state_of_charge=DataPointGeneral(value=80.0, unit=DataUnits.PERCENT),
            status=DataPointGeneral(value="active", unit=None)
        )
        assert data.state_of_charge.value == 80.0
        assert data.state_of_charge.unit == DataUnits.PERCENT
        assert data.status.value == "active"
        assert data.status.unit is None

    def test_config_data_creation(self):
        """Test creating ConfigData with DataPointGeneral fields."""
        class TestConfigData(ConfigData):
            capacity: Optional[DataPointGeneral] = None
            efficiency: Optional[DataPointGeneral] = None

        data = TestConfigData(
            capacity=DataPointGeneral(value=1000.0, unit=DataUnits.LITER),
            efficiency=DataPointGeneral(value=0.95, unit=DataUnits.PERCENT)
        )
        assert data.capacity.value == 1000.0
        assert data.capacity.unit == DataUnits.LITER
        assert data.efficiency.value == 0.95
        assert data.efficiency.unit == DataUnits.PERCENT


class TestComponentIOModel:
    """Tests for ComponentIOModel class."""

    def test_component_io_model_creation(self):
        """Test creating a ComponentIOModel with InputData and OutputData."""
        class TestInputData(InputData):
            input_field: Optional[DataPointGeneral] = None

        class TestOutputData(OutputData):
            output_field: Optional[DataPointGeneral] = None

        io_model = ComponentIOModel(
            input=TestInputData(),
            output=TestOutputData()
        )
        assert isinstance(io_model.input, TestInputData)
        assert isinstance(io_model.output, TestOutputData)


class TestComponentValidationError:
    """Tests for ComponentValidationError exception."""

    def test_component_validation_error_creation(self):
        """Test creating a ComponentValidationError."""
        error = ComponentValidationError("Test validation error")
        assert str(error) == "Test validation error"
        assert isinstance(error, Exception)


class TestUnitConversion:
    """Tests for unit conversion in ComponentData subclasses."""

    def test_input_data_unit_conversion(self):
        """Test that InputData performs unit conversion when needed."""
        class TestInputDataWithUnits(InputData):
            temperature: Optional[DataPointGeneral] = None

        # This test checks that the model can be created with different units
        # The actual conversion logic is tested in the component tests
        data = TestInputDataWithUnits(
            temperature=DataPointGeneral(value=25.0, unit=DataUnits.DEGREECELSIUS)
        )
        assert data.temperature.value == 25.0
        assert data.temperature.unit == DataUnits.DEGREECELSIUS

    def test_config_data_unit_inheritance(self):
        """Test that ConfigData properly inherits unit conversion from ComponentData."""
        class TestConfigDataWithUnits(ConfigData):
            volume: Optional[DataPointGeneral] = None

        data = TestConfigDataWithUnits(
            volume=DataPointGeneral(value=100.0, unit=DataUnits.LITER)
        )
        assert data.volume.value == 100.0
        assert data.volume.unit == DataUnits.LITER