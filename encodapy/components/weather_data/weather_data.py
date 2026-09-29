"""
Defines the WeatherData for Brightsky class.
Author: Paul Seidel
"""

from typing import Optional, Union
from datetime import datetime, timedelta, timezone
import pytz
import requests
from loguru import logger
from pydantic import ValidationError
from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.datapoints import DataPointNumber, DataPointDict, DataPointTimestep
from encodapy.utils.units import DataUnits, adjust_units

from .weather_data_config import (
    WeatherDataConfigData,
    WeatherDataInputData,
    WeatherDataOutputData,
    WeatherApiCallMethod,
    WEATHER_DATA_URL,
)


class WeatherDataApiError(RuntimeError):
    """
    Custom exception for handling errors related to the WeatherData API.
    """


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
        # Initialize with empty data, so the error-handling can always fall
        # back to the last known output (also on the very first calculate() call)
        self.output_data: WeatherDataOutputData = WeatherDataOutputData()

        self.next_time_step_current_weather: datetime
        self.next_time_step_forecast_weather: datetime

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug(
            "Hello from WeatherData! "
            "Preparing Calculation part depending in the output-configuration."
        )
        outputs_allowed_datatypes = WeatherDataOutputData.get_weather_types()
        if self.io_model is None:
            logger.error(
                "No input/output configuration found for WeatherData component. "
                "Please check the configuration."
            )
            raise ValueError("No output configuration found for WeatherData component.")
        outputs_configured = self.io_model.output

        # check which weather types are configured/used in the config and which are allowed
        # just use the ones which are configured for the api-calls (current and/or forecast)
        matched_weather_types = {
            key: value
            for key, value in outputs_allowed_datatypes.items()
            if key in outputs_configured.model_dump().keys()  # pylint: disable=no-member
        }
        available_weather_types = {
            key: value
            for key, value in matched_weather_types.items()
            if getattr(outputs_configured, key) is not None
        }

        self.unique_weather_types = list(
            dict.fromkeys(available_weather_types.values())
        )
        if not self.unique_weather_types:
            raise ValueError(
                "No weather outputs configured for WeatherData component. "
                "Configure at least one output field (current and/or forecast)."
            )

        actual_time = datetime.now(self.berlin_tz).replace(second=0)
        self.next_time_step_current_weather = actual_time
        self.next_time_step_forecast_weather = actual_time

    def get_current_weather_data(self) -> DataPointDict:
        """
        Function to get current weather data for the WeatherData component
        """
        # logic to retrieve current weather data from https://brightsky.dev/
        # https://api.brightsky.dev/current_weather?lat=51.3&lon=13.44&tz=Europe/Berlin

        output_dict = {}
        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": self.berlin_tz,
        }

        url = f"{WEATHER_DATA_URL}/current_weather"

        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code >= 400:
                error_text = response.json().get("message", response.text[:200])
                logger.error(
                    f"Getting data of brightsky failed, Client Error Codes {error_text}"
                )
                raise WeatherDataApiError(error_text)

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

            else:
                error_text = response.json().get("message", response.text[:200])
                logger.error(
                    f"Getting data of brightsky failed, Status Code: {error_text}"
                )
                raise WeatherDataApiError(error_text)

        except requests.exceptions.Timeout:
            logger.error(
                "error: The API did not respond quickly enough (timeout exceeded)."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")

        return DataPointDict(value=output_dict)

    def get_future_time(
        self, base_date: datetime, time_offset: DataPointTimestep
    ) -> datetime:
        """
        Function to calculate a future datetime based on a base date and a time_offset
        Args:
            base_date (datetime),
            time_offset (DataPointTimestep)
        Returns:
            datetime: datetime with the timedelta added to the base_date
        """

        logger.debug(
            f"Calculating future time from base_date: {base_date} "
            f"with value: {time_offset.value} and unit: {time_offset.unit}"
        )
        timeoffset_seconds = adjust_units(
            time_offset.value, time_offset.unit, DataUnits.SECOND
        )
        if timeoffset_seconds is None or not isinstance(
            timeoffset_seconds, (int, float)
        ):
            raise ValueError(
                f"Invalid time_offset value: {time_offset.value} "
                f"or unit: {time_offset.unit}. "
                "Expected a numeric value and a valid DataUnits enum."
            )

        return base_date + timedelta(seconds=timeoffset_seconds)

    def get_forecast_weather_data(self) -> DataPointDict:
        """
        Function to get forecast weather data for the WeatherData component
        from [brightsky](https://brightsky.dev/)

        Example: https://api.brightsky.dev/weather?lat=51.3&lon=13.44&tz=Europe/Berlin
        """

        logger.debug("Get Forecast Data from Brightsky...")
        actual_time = datetime.now(self.berlin_tz)
        forecast_start_time = actual_time.replace(
            minute=(actual_time.minute // 15) * 15, second=0, microsecond=0
        )

        forecast_end_time = self.get_future_time(
            forecast_start_time, self.config_data.forecast_time_range
        )

        output_dict = {}

        # parameter as dict for the api-call
        params = {
            "lat": self.config_data.latitude.value,
            "lon": self.config_data.longitude.value,
            "tz": self.berlin_tz,
            "date": forecast_start_time,
            "last_date": forecast_end_time,
        }

        url = f"{WEATHER_DATA_URL}/weather"

        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code >= 400:
                error_text = response.json().get("message", response.text[:200])
                logger.error(f"Failed read data of brightsky: {error_text}")
                raise WeatherDataApiError(error_text)

            if response.status_code == 200:
                data = response.json()

                weather = data["weather"]

                temp_dict = {hour["timestamp"]: hour["temperature"] for hour in weather}
                solar_dict = {hour["timestamp"]: hour["solar"] for hour in weather}

                output_dict = {
                    "forecast_temperature": temp_dict,
                    "forecast_solar": solar_dict,
                }
            else:
                error_text = response.json().get("message", response.text[:200])
                logger.error(f"Failed read data of brightsky: {error_text}")
                raise WeatherDataApiError(error_text)

        except requests.exceptions.Timeout:
            logger.error(
                "error: The API did not respond quickly enough (timeout exceeded)."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")

        return DataPointDict(value=output_dict)

    @staticmethod
    def _copy_output(base: WeatherDataOutputData, **overrides) -> WeatherDataOutputData:
        """
        Create a validated copy of the given output model,
        with the given field overrides applied.
        """
        fields = {
            name: getattr(base, name) for name in WeatherDataOutputData.model_fields
        }
        fields.update(overrides)
        return WeatherDataOutputData(**fields)

    def calculate(self) -> None:
        """
        Perform the calculations for the WeatherData component
        """
        output = WeatherDataOutputData()

        # check time intervals for current and forecast weather data retrieval
        time_of_timestep = datetime.now(self.berlin_tz).replace(microsecond=0)
        time_of_timestep_utc = time_of_timestep.astimezone(timezone.utc)
        logger.debug(f"Current time of timestep: {time_of_timestep}")
        logger.debug(
            "Next time step for current weather data retrieval: "
            f"{self.next_time_step_current_weather}"
        )

        if WeatherApiCallMethod.CURRENT.value in self.unique_weather_types:
            # base: last known current weather data
            output = self._copy_output(self.output_data)

            if time_of_timestep >= self.next_time_step_current_weather:
                logger.debug("Get Current Data from Brightsky...")

                try:
                    current_data = self.get_current_weather_data()
                except WeatherDataApiError as e:
                    logger.error(
                        f"Error occurred while fetching current weather data: {e}"
                    )
                    current_data = None

                if current_data is not None and current_data.value:
                    try:
                        output = WeatherDataOutputData(
                            temperature=DataPointNumber(
                                value=current_data.value.get("temperature"),
                                unit=DataUnits.DEGREECELSIUS,
                                time=time_of_timestep_utc,
                            ),
                            relative_humidity=DataPointNumber(
                                value=current_data.value.get("relative_humidity"),
                                unit=DataUnits.PERCENT,
                                time=time_of_timestep_utc,
                            ),
                            pressure_msl=DataPointNumber(
                                value=current_data.value.get("pressure_msl"),
                                unit=DataUnits.HPA,
                                time=time_of_timestep_utc,
                            ),
                            dew_point=DataPointNumber(
                                value=current_data.value.get("dew_point"),
                                unit=DataUnits.DEGREECELSIUS,
                                time=time_of_timestep_utc,
                            ),
                            solar_60=DataPointNumber(
                                value=current_data.value.get("solar_60"),
                                unit=DataUnits.B13,
                                time=time_of_timestep_utc,
                            ),
                        )
                    except ValidationError as e:
                        logger.error(
                            f"Validation error while creating WeatherDataOutputData: {e}"
                        )
                else:
                    logger.error(
                        "Current Weather Data Output is None! Using last data."
                    )

                # update next time step for current weather data retrieval
                self.next_time_step_current_weather = self.get_future_time(
                    time_of_timestep, self.config_data.time_interval_current_weather
                )

            else:
                logger.debug("Use Weather data of last API_call")

        if WeatherApiCallMethod.FORECAST.value in self.unique_weather_types:
            # base: current data of this timestep + last known forecast data
            output = self._copy_output(
                output,
                forecast_temperature=self.output_data.forecast_temperature,
                forecast_solar=self.output_data.forecast_solar,
            )

            if time_of_timestep >= self.next_time_step_forecast_weather:
                logger.debug("Get Forecast Data from Brightsky...")

                try:
                    forecast_data = self.get_forecast_weather_data()
                except WeatherDataApiError as e:
                    logger.error(
                        f"Error occurred while fetching forecast weather data: {e}"
                    )
                    forecast_data = None

                if forecast_data is not None and forecast_data.value:
                    temperature_dict = forecast_data.value.get(
                        "forecast_temperature", {}
                    )
                    solar_dict = forecast_data.value.get("forecast_solar", {})

                    try:
                        output = self._copy_output(
                            output,
                            forecast_temperature=DataPointDict(
                                value={
                                    str(index): value
                                    for index, value in temperature_dict.items()
                                },
                                unit=DataUnits.DEGREECELSIUS,
                                time=time_of_timestep_utc,
                            ),
                            forecast_solar=DataPointDict(
                                value={
                                    str(index): value
                                    for index, value in solar_dict.items()
                                },
                                unit=DataUnits.B13,
                                time=time_of_timestep_utc,
                            ),
                        )
                    except ValidationError as e:
                        logger.error(
                            f"Validation error while creating WeatherDataOutputData for forecast: {e}"
                        )
                else:
                    logger.error(
                        "Forecast Weather Data Output is None! Using last data."
                    )

                # update next time step for forecast weather data retrieval
                self.next_time_step_forecast_weather = self.get_future_time(
                    time_of_timestep, self.config_data.time_interval_forecast_weather
                )

            else:
                logger.debug("Use Weather data of last API_call")

        self.output_data = output
