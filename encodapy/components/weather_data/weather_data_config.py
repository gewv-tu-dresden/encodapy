"""
Defines the configuration data models for the WeatherData via Brightsky component.
Author: Paul Seidel, Martin Altenburger
"""

from typing import Optional, Dict
from enum import Enum
from pydantic import Field
from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import (
    DataPointNumber,
    DataPointDict,
    DataPointTimestep,
)
from encodapy.utils.units import DataUnits

WEATHER_DATA_URL = "https://api.brightsky.dev"
WEATHER_DATA_UNITS = "si"  # use "si" for Brightsky data
WEATHER_DATA_TZ_NAME = "Europe/Berlin"  # use "Europe/Berlin" for Brightsky/DWD data


class WeatherApiCallMethod(Enum):
    """
    Enum for the API call methods of the weather data service.

    Members:
        CURRENT: Retrieve current weather data
        FORECAST: Retrieve weather forecast data
    """

    CURRENT = "current"
    FORECAST = "forecast"


class WeatherDataInputData(InputData):
    """
    Input model for the WeatherData component

    There is actually no input nessessary for this component, but maybe in future version.
    """


class WeatherDataOutputData(OutputData):
    """
    Output model for the WeatherData component

    If you like to add a validator, see the documentation for \
        :class:`~encodapy.components.basic_component_config.ComponentData`
    """

    temperature: Optional[DataPointNumber] = Field(
        None,
        description="Air temperature at timestamp, 2 m above the ground in degree celsius",
        json_schema_extra={"unit": "CEL", "weather_type": "current"},
    )
    relative_humidity: Optional[DataPointNumber] = Field(
        None,
        description="Relative humidity at timestamp in %",
        json_schema_extra={"unit": "P1", "weather_type": "current"},
    )
    pressure_msl: Optional[DataPointNumber] = Field(
        None,
        description="Atmospheric pressure at timestamp, reduced to mean sea level in hPa",
        json_schema_extra={"unit": "PAL", "weather_type": "current"},
    )
    dew_point: Optional[DataPointNumber] = Field(
        None,
        description="Dew point at timestamp, 2 m above ground in degree celsius",
        json_schema_extra={"unit": "CEL", "weather_type": "current"},
    )
    solar_60: Optional[DataPointNumber] = Field(
        None,
        description="Solar irradiation during previous 60 minutes in J / m²",
        json_schema_extra={"unit": "B13", "weather_type": "current"},
    )
    forecast_temperature: Optional[DataPointDict] = Field(
        None,
        description="Forecast temperature data",
        json_schema_extra={"unit": "CEL", "weather_type": "forecast"},
    )
    forecast_solar: Optional[DataPointDict] = Field(
        None,
        description="Forecast solar irradiation data during previous 60 minutes in J/m²",
        json_schema_extra={"unit": "B13", "weather_type": "forecast"},
    )

    @classmethod
    def get_weather_types(cls) -> Dict[str, str]:
        """
        get a dict with {key: weather_type} for all fields in this class,
        which defines "weather_type" in json_schema_extra.
        """
        weather_types: Dict[str, str] = {}
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra
            if isinstance(extra, dict):
                weather_type = extra.get("weather_type")
                if isinstance(weather_type, str):
                    weather_types[name] = weather_type
        return weather_types


class WeatherDataConfigData(ConfigData):
    """
    Config data model for the WeatherData  component

    If you like to add a validator, see the documentation for \
        :class:`~encodapy.components.basic_component_config.ComponentData`
    """

    longitude: DataPointNumber = Field(
        DataPointNumber(value=13.4),
        description="""Value of longitude of the chosen location in degree
        (default value for Berlin)""",
        json_schema_extra={"unit": "DD"},
    )
    latitude: DataPointNumber = Field(
        DataPointNumber(value=52.5),
        description="Value of latitude of the chosen location in degree (default value for Berlin)",
        json_schema_extra={"unit": "DD"},
    )
    forecast_time_range: DataPointTimestep = Field(
        DataPointTimestep(value=1, unit=DataUnits.DAY),
        description="""Forecast time range (for the of last weather forecast) to retrieve.
        Default value is set to 1 day.""",
    )
    time_interval_current_weather: DataPointTimestep = Field(
        DataPointTimestep(value=15, unit=DataUnits.MINUTE),
        description="""Time interval for current weather data retrieval.
        Default value is set to 15 minutes.""",
    )
    time_interval_forecast_weather: DataPointTimestep = Field(
        DataPointTimestep(value=3, unit=DataUnits.HOUR),
        description="""Time interval for forecast weather data retrieval.
        Default value is set to 3 hours.""",
    )
