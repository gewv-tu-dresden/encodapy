"""
Description: Configuration model for the two-point controller component.
Author: Martin Altenburger
"""

from pydantic import Field, model_validator
from loguru import logger
from encodapy.components.basic_component_config import (
    InputData,
    OutputData,
    ConfigData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber
from encodapy.utils.units import get_unit_adjustment_factor


class TwoPointControllerInputData(InputData):
    """
    Model for the input of the two-point controller component.
    
    Attributes:
        current_value (DataPointNumber): The current value of the input.
        latest_control_signal (DataPointNumber): The latest control signal output \
            from the two-point controller.
    """

    current_value: DataPointNumber = Field(
        ..., description="Current value of the input, typically a sensor reading"
    )
    latest_control_signal: DataPointNumber = Field(
        ..., description="Latest control signal output from the two-point controller"
    )

class TwoPointControllerOutputData(OutputData):
    """
    Model for the output of the two-point controller component.

    Attributes:
        control_signal (DataPointNumber): The control signal output from the two-point controller.
    """

    control_signal: DataPointGeneral = Field(
        ..., description="Control signal output from the two-point controller"
    )


class TwoPointControllerConfigData(ConfigData):
    """
    Model for the configuration data of the thermal storage service.
    """

    hysteresis: DataPointNumber = Field(
        ...,
        description="Hysteresis value for the two-point controller",
    )
    setpoint: DataPointNumber = Field(
        ...,
        description="Setpoint value for the two-point controller",
    )
    command_enabled: DataPointGeneral = Field(
        DataPointGeneral(value=1),
        description="Value representing the enabled state of the control signal",
    )
    command_disabled: DataPointGeneral = Field(
        DataPointGeneral(value=0),
        description="Value representing the disabled state of the control signal",
    )

    @model_validator(mode="after")
    def check_unit_setpoint(self):
        """
        Validator to check if the units of hysteresis and setpoint are the same.
        If not, it tries to convert the hysteresis to the unit of the setpoint.


        """
        hysteresis = DataPointNumber.model_validate(self.hysteresis)
        setpoint = DataPointNumber.model_validate(self.setpoint)
        if (
            hysteresis.unit != setpoint.unit
            and hysteresis.unit is not None
            and setpoint.unit is not None
        ):
            logger.warning(
                f"Units of hysteresis ({hysteresis.unit}) and setpoint ({setpoint.unit}) "
                "are not the same. Please check your configuration."
            )
            unit_adjustment_factor = get_unit_adjustment_factor(
                unit_actual=hysteresis.unit, unit_target=setpoint.unit
            )
            if unit_adjustment_factor is None:
                logger.warning(
                    f"Unit of hysteresis is {hysteresis.unit}, but expected {setpoint.unit}. "
                    "Could not convert, because units are not compatible "
                    "or no adjustment factor found."
                )
                return self

            hysteresis.value *= unit_adjustment_factor
            hysteresis.unit = setpoint.unit
        self.hysteresis = DataPointNumber(value=hysteresis.value, unit=hysteresis.unit)
        return self
