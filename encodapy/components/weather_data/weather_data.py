"""
Defines the OpenWeatherMapData class.
Author: Paul Seidel
"""

from typing import Optional, Union

from loguru import logger
from datetime import datetime, timedelta, timezone
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
        self.unique_weather_types: list[str] = []
        self.berlin_tz = pytz.timezone("Europe/Berlin")

        # Add the type declaration for the following variables so that autofill works properly
        self.config_data: WeatherDataConfigData
        self.input_data: WeatherDataInputData
        self.output_data: WeatherDataOutputData

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )

        # Component-specific initialization logic

        self.time_interval_current_weather: str = self.config_data.time_interval_current_weather.value
        self.time_interval_forecast_weather: str = self.config_data.time_interval_forecast_weather.value  
        #self.next_time_step_current_weather: datetime = None
        #self.next_time_step_forecast_weather: datetime = None
      

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug("Hello from WeatherData! Preparing Calculation part depending in the output-configuration.")
        outputs_allowed_datatypes =  WeatherDataOutputData.get_weather_types()
        outputs_configured = self.io_model.output

        # check which weather types are configured/used in the config and which are allowed
        # just use the ones which are configured for the api-calls (current and/or forecast) 
        matched_weather_types = {
            key: value
            for key, value in outputs_allowed_datatypes.items()
            if key in outputs_configured.model_dump().keys()
            }
        available_weather_types = {
            key: value
            for key, value in matched_weather_types.items()
            if getattr(outputs_configured, key) is not None
            }
        
        self.unique_weather_types = list(dict.fromkeys(available_weather_types.values()))

        
        actual_time = datetime.now(self.berlin_tz).replace(second=0) 
        self.next_time_step_current_weather = actual_time
        self.next_time_step_forecast_weather = actual_time


    def get_current_weather_data(self) -> DataPointDict:
        """
        Function to get current weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/current_weather?lat=51.3&lon=13.44&tz=Europe/Berlin

        
        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": self.berlin_tz 
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

    def get_future_time_string(self, base_date, time_str):
        '''
        Uses regex to separate the number and the letter (unit)
        Input: base_date (datetime), time_str (str) e.g. "15M", "2d" or "4h"
        Output: datetime object with the calculated date and time with the timedelta added to the base_date  
        '''
        match = re.match(r"(\d+)([dhM])", time_str.strip())
        if not match:
            raise ValueError(f"Invalid format: {time_str}. Use e.g., '15M', '2d' or '4h'.")
        
        value = int(match.group(1))
        unit = match.group(2)
        logger.debug(f"Calculating future time from base_date: {base_date} with value: {value} and unit: {unit}")
    
        # calculating matching timedelta 
        if unit == 'd':
            return base_date + timedelta(days=value)
        elif unit == 'h':
            return base_date + timedelta(hours=value)
        elif unit == 'M':
            return base_date + timedelta(minutes=value)

    def get_forecast_weather_data(self) -> DataPointDict:
        """
        Function to get forecast weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/weather?lat=51.3&lon=13.44&tz=Europe/Berlin
                
        actual_time = datetime.now(self.berlin_tz).strftime("%Y-%m-%dT%H:%M")
        forecast_start_time = datetime.fromisoformat(actual_time).replace(minute=(datetime.fromisoformat(actual_time).minute // 15) * 15, second=0, microsecond=0)
        forecast_time_delta = self.config_data.forecast_time_range.value
        forecast_end_time = self.get_future_time_string(forecast_start_time, forecast_time_delta)
        
        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": self.berlin_tz ,
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
        output = WeatherDataOutputData()

        # check time intervals for current and forecast weather data retrieval
        time_of_timestep = datetime.now(self.berlin_tz).replace(microsecond=0)
        time_of_timestep_utc = time_of_timestep.astimezone(timezone.utc)
        logger.debug(f"Current time of timestep: {time_of_timestep}")
        logger.debug(f"Next time step for current weather data retrieval: {self.next_time_step_current_weather}")

        if WeatherApiCallMethod.CURRENT.value in self.unique_weather_types:
            if time_of_timestep >= self.next_time_step_current_weather:
                logger.debug("Get Current Data from Brightsky...")

                current_data = self.get_current_weather_data()

                output = WeatherDataOutputData(
                    temperature=DataPointNumber(value=current_data.value.get("temperature"), unit=DataUnits.DEGREECELSIUS, time=time_of_timestep_utc),
                    relative_humidity=DataPointNumber(value=current_data.value.get("relative_humidity"), unit=DataUnits.PERCENT, time=time_of_timestep_utc),
                    pressure_msl=DataPointNumber(value=current_data.value.get("pressure_msl"), unit=DataUnits.HPA, time=time_of_timestep_utc),
                    dew_point=DataPointNumber(value=current_data.value.get("dew_point"), unit=DataUnits.DEGREECELSIUS, time=time_of_timestep_utc),
                    solar_60=DataPointNumber(value=current_data.value.get("solar_60"), unit=DataUnits.KWM, time=time_of_timestep_utc)
                )
                
                # update next time step for current weather data retrieval
                self.next_time_step_current_weather = self.get_future_time_string(time_of_timestep, self.time_interval_current_weather)
                
            else: 
                logger.debug("Use Weather data of last API_call")
                output = WeatherDataOutputData(
                    temperature = self.output_data.temperature,
                    relative_humidity=self.output_data.relative_humidity,
                    pressure_msl=self.output_data.pressure_msl,
                    dew_point= self.output_data.dew_point,
                    solar_60=self.output_data.solar_60
                )
                
        if WeatherApiCallMethod.FORECAST.value in self.unique_weather_types:
            if time_of_timestep >= self.next_time_step_forecast_weather:
                logger.debug("Get Forecast Data from Brightsky...")
    
                forecast_data = WeatherData.get_forecast_weather_data(self)
                    
                temperature_dict = forecast_data.value.get('forecast_temperature', {})
                solar_dict = forecast_data.value.get('forecast_solar', {})
            
                output.forecast_temperature = DataPointDict(
                        value={str(index): value for index, value in temperature_dict.items()}, unit=DataUnits.DEGREECELSIUS, time=time_of_timestep_utc
                        )
                output.forecast_solar = DataPointDict(
                        value={str(index): value for index, value in solar_dict.items()}, unit=DataUnits.KWM, time=time_of_timestep_utc
                        )

                # update next time step for current weather data retrieval
                self.next_time_step_forecast_weather = self.get_future_time_string(time_of_timestep, self.time_interval_forecast_weather)
                
            else:
                logger.debug("Use Weather data of last API_call")
                output.forecast_temperature = self.output_data.forecast_temperature
                output.forecast_solar = self.output_data.forecast_solar
                

        if not any(weather_type in self.unique_weather_types for weather_type in [WeatherApiCallMethod.CURRENT.value, WeatherApiCallMethod.FORECAST.value]):
           logger.error(
                f"Invalid weather_call_method: {self.config_data.weather_type.value}. Expected 'current' or 'forecast'."
             )

           
        self.output_data = output
