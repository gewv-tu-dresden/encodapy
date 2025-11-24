"""
Basic configuration for the components in the EnCoCaPy framework.
Author: Martin Altenburger
"""

from typing import Dict, Optional

from loguru import logger
from pydantic import BaseModel, Field, RootModel, model_validator

from encodapy.utils.units import DataUnits, get_unit_adjustment_factor
from encodapy.utils.datapoints import DataPointGeneral


# Models for the Input Configuration
class IOAllocationModel(BaseModel):
    """
    Model for the input or output allocation.

    Attributes:
        entity (str): ID of the entity to which the input or output is allocated
        attribute (str): ID of the attribute to which the input or output is allocated
    """

    entity: str = Field(
        ..., description="ID of the entity to which the input or output is allocated"
    )
    attribute: str = Field(
        ..., description="ID of the attribute to which the input or output is allocated"
    )


class IOModell(
    (RootModel[Dict[str, IOAllocationModel]])
):  # pylint: disable=too-few-public-methods
    """
    Model for the input, staticdata and output of a component.

    It contains a dictionary with the key as the ID of the input, output or static data
    and the value as the allocation model
    
    See also :class:`~encodapy.components.basic_component_config.IOAllocationModel`.

    There is no validation for this.
    It is used to create the the ComponentIOModel for each component.
    """


class ConfigDataPoints(
    (RootModel[Dict[str, IOAllocationModel | DataPointGeneral]])
):  # pylint: disable=too-few-public-methods
    """
    Model for the configuration of config data points.
    
    See also :class:`~encodapy.components.basic_component_config.IOAllocationModel` and
    :class:`~encodapy.utils.datapoints.DataPointGeneral`.
    """


class ControllerComponentModel(BaseModel):
    """
    Model for the configuration of the controller components.
    
    Attributes:
        active (bool): Whether the component is active or not
        id (str): The id of the component
        type (str): The type of the component (e.g. thermal storage, heat pump, etc. / \
            needs to be defined for individual components)
        inputs (IOModell): The inputs of the component as a dictionary with IOAllocationModel \
            for the individual inputs
        outputs (IOModell): The outputs of the component as a dictionary with IOAllocationModel \
            for the individual outputs
        config (ConfigDataPoints): The configuration of the component as a dictionary with \
            IOAllocationModel for the individual static data or DataPointModel with direct values
    """

    active: Optional[bool] = True
    id: str
    type: str
    inputs: IOModell
    outputs: IOModell
    config: Optional[ConfigDataPoints] = None


# Models for the internal input and output connections, needs to filled for the components
class ComponentData(BaseModel):
    """
    Basemodel for the configuration of the datapoints of a component

    Base for :class:`~encodapy.components.basic_component_config.InputData`, \
        :class:`~encodapy.components.basic_component_config.OutputData`\
        and :class:`~encodapy.components.basic_component_config.ConfigData`
    
    Provides a validator to check the units of the input values \
        and convert them if necessary.
    """

    @model_validator(mode="after")
    def check_unit_values(self) -> "ComponentData":
        """
        Check the units of the input values and convert them if necessary.
        """
        for name, field in self.model_fields.items():
            value = getattr(self, name)
            extra = field.json_schema_extra or {}
            if not isinstance(extra, dict):
                logger.warning(f"Extra for field {name} is not a dictionary: {extra}")
                continue

            if isinstance(value, DataPointGeneral):
                if "unit" in extra.keys() and value.unit is None:
                    value.unit = DataUnits(extra["unit"])
                elif (
                    "unit" in extra.keys()
                    and value.unit is not None
                    and value.unit != DataUnits(extra["unit"])
                ):
                    if value.value is None or not isinstance(value.value, (int, float)):
                        logger.warning(
                            f"Unit of {name} is {value.unit}, but expected {extra['unit']}. "
                            f"Could not convert, because value is None or not a number."
                        )
                        continue
                    unit_adjustment_factor = get_unit_adjustment_factor(
                        unit_actual=value.unit, unit_target=DataUnits(extra["unit"])
                    )
                    if unit_adjustment_factor is None:
                        logger.warning(
                            f"Unit of {name} is {value.unit}, but expected {extra['unit']}. "
                            f"Could not convert, because units are not compatible "
                            "or no adjustment factor found."
                        )
                        continue
                    value.value = value.value * unit_adjustment_factor
                    value.unit = DataUnits(extra["unit"])
        return self


class OutputData(ComponentData):
    """
    Base model for the component output configuration.

    Subclass this and declare fields for each output datapoint. OutputData
    inherits the unit-checking validator from \
        :class:`~encodapy.components.basic_component_config.ComponentData`,
    which will validate and convert units when possible.

    Fields should be instances of :class:`~encodapy.utils.datapoints.DataPointGeneral`
    (or subclasses thereof) so the validator can handle unit and value conversion.

    Needs to be implemented for the specific component.
    """


class InputData(ComponentData):
    """
    Base model for the component input configuration.

    Subclass this and declare fields for each input datapoint. InputData
    inherits the unit-checking validator from \
        :class:`~encodapy.components.basic_component_config.ComponentData`,
    which will validate and convert units when possible.

    Fields should be instances of :class:`~encodapy.utils.datapoints.DataPointGeneral`
    (or subclasses thereof) so the validator can handle unit and value conversion.
    
    Needs to be implemented for the specific component.
    """

class ConfigData(ComponentData):
    """
    Base model for the component static configuration data.

    Subclass this and declare fields for each static configuration datapoint. ConfigData
    inherits the unit-checking validator from \
        :class:`~encodapy.components.basic_component_config.ComponentData`,
    which will validate and convert units when possible.

    Fields should be instances of :class:`~encodapy.utils.datapoints.DataPointGeneral`
    (or subclasses thereof) so the validator can handle unit and value conversion.

    Needs to be implemented by the user if static configuration is required.
    """

class ComponentIOModel(BaseModel):
    """
    Model for the input and output of the thermal storage service.

    Attributes:
        input (:class:`~encodapy.utils.datapoints.InputModel`): \
            Input configuration for the thermal storage service
        output (:class:`~encodapy.utils.datapoints.OutputModel`): \
            Output configuration for the thermal storage service
    """

    input: InputData = Field(
        ..., description="Input configuration for the thermal storage service"
    )
    output: OutputData = Field(
        ..., description="Output configuration for the thermal storage service"
    )


# Custom Exceptions
class ComponentValidationError(Exception):
    """Custom error for invalid configurations."""
