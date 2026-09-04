"""
Defines the configuration data models for the OpenWeatherMap component.
Author: Paul Seidel
"""

from typing import Optional
from enum import Enum

from pydantic import Field

from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber, DataPointString
from encodapy.utils.units import DataUnits


class WeatherDataInputData(InputData):
    """
    Input model for the WeatherData component
    
    There is actually no input nessessary for this component, but maybe in future version.
    """

    #a_general_input: DataPointGeneral = Field(
    #    ...,
    #    description="""A general input of the WeatherData component,
    #    Any values allowed, None from MQTT also allowed""",
    #)
    #a_number_input: DataPointNumber = Field(
    #    ...,
    #    description="A number input of the WeatherData component",
    #    json_schema_extra={"unit": "CEL"},
    #)
    #another_number_input: DataPointNumber = Field(
    #    DataPointNumber(value=10, unit=DataUnits.KELVIN),
    #    description="""Another number input of the WeatherData component,
    #    with a default value of 10 so no value from inputs is required""",
    #    json_schema_extra={"unit": "KEL"},
    #)


class WeatherDataOutputData(OutputData):
    """
    Output model for the WeatherData component
    
    If you like to add a validator, see the documentation for \
        :class:`~encodapy.components.basic_component_config.ComponentData`
    """

    temperature: Optional[DataPointNumber] = Field(
        None,
        description="Air temperature at timestamp, 2 m above the ground in degree celsius",
        json_schema_extra={"unit": "CEL"},
        )
    relative_humidity: Optional[DataPointNumber] = Field(
        None,
        description="Relative humidity at timestamp in %",
        json_schema_extra={"unit": "P1"},
        )
    pressure_msl: Optional[DataPointNumber]  = Field(
        None,
        description="Atmospheric pressure at timestamp, reduced to mean sea level in hPa",
        json_schema_extra={"unit": "A97"},
        )
    dew_point: Optional[DataPointNumber] = Field(
        None,
        description="Dew point at timestamp, 2 m above ground in degree celsius",
        json_schema_extra={"unit": "CEL"},
        )
    solar_60: Optional[DataPointNumber] = Field(
        None,
        description="Solar irradiation during previous 60 minutes in kWh / m²",
        json_schema_extra={"unit": "KWM"},
        )
    
class WeatherApiCallMethod(Enum):
    """
    Enum for the API call methods of the weather data service.

    Members:
        CURRENT: Retrieve current weather data
        FORECAST: Retrieve weather forecast data
    """

    CURRENT = "current"
    FORECAST = "forecast"


class DataPointWeatherApiCallMethod(DataPointGeneral):
    """
    Model for datapoints of the controller component which define the API call method.

    Attributes:
        value: The value of the datapoint, which is a string representing the API call method
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    value: WeatherApiCallMethod

class WeatherDataConfigData(ConfigData):
    """
    Config data model for the WeatherData  component
    
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

    weather_type: DataPointWeatherApiCallMethod = Field(
        DataPointWeatherApiCallMethod(
            value=WeatherApiCallMethod.CURRENT
        ),
        description="API call method for retrieving weather data (default is 'current' for current weather data)",
    )
