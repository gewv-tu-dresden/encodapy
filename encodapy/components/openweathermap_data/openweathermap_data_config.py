"""
Defines the configuration data models for the OpenWeatherMap component.
"""

from typing import Optional

from pydantic import Field

from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber
from encodapy.utils.units import DataUnits


class OpenweathermapDataInputData(InputData):
    """
    Input model for the Openweathermap component
    
    There is actually no input nessessary for this component, but maybe in future version.
    """

    #a_general_input: DataPointGeneral = Field(
    #    ...,
    #    description="""A general input of the Openweathermap component,
    #    Any values allowed, None from MQTT also allowed""",
    #)
    #a_number_input: DataPointNumber = Field(
    #    ...,
    #    description="A number input of the Openweathermap component",
    #    json_schema_extra={"unit": "CEL"},
    #)
    #another_number_input: DataPointNumber = Field(
    #    DataPointNumber(value=10, unit=DataUnits.KELVIN),
    #    description="""Another number input of the Openweathermap component,
    #    with a default value of 10 so no value from inputs is required""",
    #    json_schema_extra={"unit": "KEL"},
    #)


class OpenweathermapDataOutputData(OutputData):
    """
    Output model for the Openweathermap component
    
    If you like to add a validator, see the documentation for \
        :class:`~encodapy.components.basic_component_config.ComponentData`
    """

    t_ambient: DataPointNumber = Field(
        None,
        description="Output of the Openweathermap component, the ambient temperature in degree celsius",
        json_schema_extra={"unit": "CEL"},
        )


class OpenweathermapDataConfigData(ConfigData):
    """
    Config data model for the Openweathermap component
    
    If you like to add a validator, see the documentation for \
        :class:`~encodapy.components.basic_component_config.ComponentData`
    """

    longitude: DataPointGeneral = Field(
        DataPointNumber(value=13.4),
        description="Value of longitude of the chosen location in degree (default value for Berlin)",
        json_schema_extra={"unit": "DD"}
    )
    latitude: DataPointGeneral = Field(
        DataPointNumber(value=52.5),
        description="Value of latitude of the chosen location in degree (default value for Berlin)",
        json_schema_extra={"unit": "DD"}
    )
