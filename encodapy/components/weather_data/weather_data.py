"""
Defines the OpenWeatherMapData class.
Author: Paul Seidel
"""

from typing import Optional, Union

from loguru import logger
from datetime import datetime, timedelta
import re
import pytz
import requests

from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.datapoints import DataPointNumber, DataPointDict
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

    def get_current_weather_data(self) -> DataPointDict:
        """
        Function to get current weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/current_weather?lat=51.3&lon=13.44&tz=Europe/Berlin

        berlin_tz = pytz.timezone("Europe/Berlin")
        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": berlin_tz 
        }

        url = "https://api.brightsky.dev/current_weather"

        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code >= 400:
                error_text = response.json()["message"]
                logger.debug(f"Failed read data of brightsky: {error_text}")
                raise Exception(error_text)

            if response.status_code == 200:
                data = response.json()
                weather = data["weather"]

                output_dict = {
                    "temperature": float(weather["temperature"]),
                    "relative_humidity": float(weather["relative_humidity"]),
                    "pressure_msl": float(weather["pressure_msl"]),
                    "dew_point": float(weather["dew_point"]),
                    "solar_60": float(weather["solar_60"]),
                }

        except requests.exceptions.Timeout:
            logger.error("error: The API did not respond quickly enough (timeout exceeded).")
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")

        return DataPointDict(value=output_dict)

    def get_forecast_time_string(self, base_date, time_str):
        '''
        Uses regex to separate the number and the letter (unit)
        Input: base_date (datetime), time_str (str) e.g. "2d" or "4h"
        Output: datetime object with the calculated date and time (end of forecast)  
        '''
        match = re.match(r"(\d+)([dh])", time_str.strip().lower())
        if not match:
            raise ValueError(f"Invalid format: {time_str}. Use e.g., '2d' or '4h'.")
        
        value = int(match.group(1))
        unit = match.group(2)
    
        # calculating matching timedelta 
        if unit == 'd':
            return base_date + timedelta(days=value)
        elif unit == 'h':
            return base_date + timedelta(hours=value)

    def get_forecast_weather_data(self) -> DataPointDict:
        """
        Function to get forecast weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/weather?lat=51.3&lon=13.44&tz=Europe/Berlin
                
        berlin_tz = pytz.timezone("Europe/Berlin")
        actual_time = datetime.now(berlin_tz).strftime("%Y-%m-%dT%H:%M")
        forecast_start_time = datetime.fromisoformat(actual_time).replace(minute=(datetime.fromisoformat(actual_time).minute // 15) * 15, second=0, microsecond=0)
        forecast_time_delta = self.config_data.forecast_time_range.value
        forecast_end_time = self.get_forecast_time_string(forecast_start_time, forecast_time_delta)
        
        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": berlin_tz ,
            "date": forecast_start_time,
            "last_date": forecast_end_time
            }
        
        url = "https://api.brightsky.dev/weather"
        
        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code >= 400:
                error_text = response.json()["message"]
                logger.debug(f"Failed read data of brightsky: {error_text}")
                raise Exception(error_text)

            if response.status_code == 200:
                data = response.json()
                
                weather = data["weather"]
  
                temp_dict = {hour["timestamp"]: hour["temperature"] for hour in weather}
                solar_dict = {hour["timestamp"]: hour["solar"] for hour in weather}

                output_dict = {
                    "forecast_temperature": temp_dict,
                    "forecast_solar": solar_dict
                }

        except requests.exceptions.Timeout:
            logger.error("error: The API did not respond quickly enough (timeout exceeded).")
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")
        
        return DataPointDict(value=output_dict)

    def calculate(self) -> None:
        """
        Perform the calculations for the WeatherData component
        """

        match self.config_data.weather_type.value:
            case WeatherApiCallMethod.CURRENT:
                logger.debug("Get Current Data in WeatherData...")

                output_data = self.get_current_weather_data()

                self.output_data = WeatherDataOutputData(
                        temperature=DataPointNumber(value=output_data.value.get("temperature"), unit=DataUnits.DEGREECELSIUS),
                        relative_humidity=DataPointNumber(value=output_data.value.get("relative_humidity"), unit=DataUnits.PERCENT),
                        pressure_msl=DataPointNumber(value=output_data.value.get("pressure_msl"), unit=DataUnits.HPA),
                        dew_point=DataPointNumber(value=output_data.value.get("dew_point"), unit=DataUnits.DEGREECELSIUS),
                        solar_60=DataPointNumber(value=output_data.value.get("solar_60"), unit=DataUnits.KWM),
                        )
                
            case WeatherApiCallMethod.FORECAST:
                logger.debug("Get Forecast Data in WeatherData...")
 
                data = WeatherData.get_forecast_weather_data(self)
                logger.debug(f"Forecast data retrieved: {data.value}")
                
                temperature_dict = data.value.get('forecast_temperature', {})
                solar_dict = data.value.get('forecast_solar', {})
            
                forecast_temperature = DataPointDict(
                    value={str(index): value for index, value in temperature_dict.items()}, unit=DataUnits.DEGREECELSIUS
                    )
                forecast_solar = DataPointDict(
                    value={str(index): value for index, value in solar_dict.items()}, unit=DataUnits.KWM
                    )

                self.output_data = WeatherDataOutputData(
                        forecast_temperature=forecast_temperature,
                        forecast_solar=forecast_solar
                        )
            case _ :
                logger.error(
                f"Invalid weather_call_method: {self.config_data.weather_type.value}. Expected 'current' or 'forecast'."
                )
