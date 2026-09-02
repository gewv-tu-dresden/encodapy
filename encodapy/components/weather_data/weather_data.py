"""
Defines the OpenWeatherMapData class.
Author: Paul Seidel
"""

from typing import Optional, Union

from loguru import logger
from datetime import datetime
import pytz

from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.datapoints import DataPointNumber
from encodapy.utils.units import DataUnits

from .weather_data_config import (
    WeatherDataConfigData,
    WeatherDataInputData,
    WeatherDataOutputData,
    WeatherApiCallMethod,
)


class WeatherData(BasicComponent):
    """
    Class for the OpenWeatherMap component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here
        self.example_variable: float = 1

        # Add the type declaration for the following variables so that autofill works properly
        self.config_data: WeatherDataConfigData
        self.input_data: WeatherDataInputData
        self.output_data: WeatherDataOutputData

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug("Hello from WeatherData! Preparing...")

    def get_current_weather_data(self) -> DataPointNumber:
        """
        Example function to get current weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/current_weather?lat=51.3&lon=13.44&date=2026-08-27
        logger.debug("collect input data fpr API_Call of brightsky.")
        
        latitude = self.config_data.latitude.value
        longitude = self.config_data.longitude.value
        berlin_tz = pytz.timezone("Europe/Berlin")
        time = datetime.now(berlin_tz).strftime("%Y-%m-%dT%H:%M")
        logger.debug(f"API_Call: {latitude}, {longitude}, {time}")
        


        return DataPointNumber(value=a_number, unit=DataUnits.DEGREECELSIUS)

    def get_forecast_weather_data(self) -> DataPointNumber:
        """
        Example calculation function for the WeatherData component
        """
        # Example calculation logic using the input data stored in the component
        logger.error("Calculating forecast_weather_data not implemented yet.")
        another_number = (
            42
            if self.input_data.another_number_input.value is None
            else self.input_data.another_number_input.value
        )
        return DataPointNumber(value=another_number, unit=DataUnits.DEGREECELSIUS)

    def calculate(self) -> None:
        """
        Perform the calculations for the WeatherData component
        """

        match self.config_data.weather_type.value:
            case WeatherApiCallMethod.CURRENT:
                logger.debug("Get Data in WeatherData...")
                self.output_data = WeatherDataOutputData(
                        t_ambient=self.get_current_weather_data(),
                        )
            case WeatherApiCallMethod.FORECAST:
                logger.debug("Get Data in WeatherData...")
                self.output_data = WeatherDataOutputData(
                        t_ambient=self.get_forecast_weather_data(),
                        )
            case _ :
                logger.error(
                f"Invalid weather_call_method: {self.config_data.weather_type.value}. Expected 'current' or 'forecast'."
                )
