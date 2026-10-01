"""
Defines the WeatherData via Brightsky component.
Author: Paul Seidel, Martin Altenburger
"""

from typing import Optional, Union
from json.decoder import JSONDecodeError
from datetime import datetime, timedelta, timezone
import requests
import pytz
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
    WEATHER_DATA_UNITS,
    WEATHER_DATA_TZ_NAME,
)

WEATHER_DATA_TZ = pytz.timezone(WEATHER_DATA_TZ_NAME)


class WeatherDataApiError(RuntimeError):
    """
    Custom exception for handling errors related to the WeatherData API.
    """


class WeatherData(BasicComponent):
    """
    Class for the WeatherData via Brightsky component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here
        self.unique_weather_types: list[str] = []

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

        actual_time = datetime.now(WEATHER_DATA_TZ).replace(second=0)
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
            "tz": WEATHER_DATA_TZ_NAME,
            "units": WEATHER_DATA_UNITS,
        }

        url = f"{WEATHER_DATA_URL}/current_weather"

        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code != 200:
                error_text = response.json().get("message", response.text[:200])
                logger.error(
                    f"Getting data of brightsky failed, Client Error Codes {error_text}"
                )
                raise WeatherDataApiError(error_text)

            data = response.json()
            weather = data["weather"]

            output_dict = {
                "temperature": float(weather["temperature"]),
                "relative_humidity": float(weather["relative_humidity"]),
                "pressure_msl": float(weather["pressure_msl"]),
                "dew_point": float(weather["dew_point"]),
                "solar_60": adjust_units(
                    float(weather["solar_60"]), DataUnits.KWH_MQ, DataUnits.B13
                ),
            }

        except requests.exceptions.Timeout:
            logger.error(
                "error: The API did not respond quickly enough (timeout exceeded)."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")
        except JSONDecodeError as e:
            logger.error(f"Error decoding JSON response: {e}")

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
        actual_time = datetime.now(WEATHER_DATA_TZ)
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
            "tz": WEATHER_DATA_TZ_NAME,
            "date": forecast_start_time.isoformat(),
            "last_date": forecast_end_time.isoformat(),
            "units": WEATHER_DATA_UNITS,
        }

        url = f"{WEATHER_DATA_URL}/weather"

        try:
            response = requests.get(url, params=params, timeout=5.0)
            if response.status_code != 200:
                error_text = response.json().get("message", response.text[:200])
                logger.error(f"Failed read data of brightsky: {error_text}")
                raise WeatherDataApiError(error_text)

            data = response.json()

            weather = data["weather"]

            temp_dict = {hour["timestamp"]: hour["temperature"] for hour in weather}
            solar_dict = {hour["timestamp"]: hour["solar"] for hour in weather}

            output_dict = {
                "forecast_temperature": temp_dict,
                "forecast_solar": adjust_units(
                    solar_dict, DataUnits.KWH_MQ, DataUnits.B13
                ),
            }

        except requests.exceptions.Timeout:
            logger.error(
                "error: The API did not respond quickly enough (timeout exceeded)."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection- or API-error: {e}")
        except JSONDecodeError as e:
            logger.error(f"Error decoding JSON response: {e}")

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

    def _update_current_weather(
        self,
        time_of_timestep: datetime,
        time_of_timestep_utc: datetime,
    ) -> WeatherDataOutputData:
        """
        Update the current weather data of the last known output.
        Falls back to the last known data on API, data or validation errors.

        Returns the updated output data.
        """
        # base: last known current weather data
        output = self._copy_output(self.output_data)

        if time_of_timestep < self.next_time_step_current_weather:
            logger.debug("Use Weather data of last API_call")
            return output

        logger.debug("Get Current Data from Brightsky...")

        try:
            current_data = self.get_current_weather_data()
        except WeatherDataApiError as e:
            logger.error(f"Error occurred while fetching current weather data: {e}")
            current_data = None

        if current_data is None or not current_data.value:
            logger.error("Current Weather Data Output is None! Using last data.")
            return output

        try:
            output = self._copy_output(
                self.output_data,
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
            logger.error(f"Validation error while creating WeatherDataOutputData: {e}")
            return output

        # update next time step for current weather data retrieval
        self.next_time_step_current_weather = self.get_future_time(
            time_of_timestep, self.config_data.time_interval_current_weather
        )
        return output

    def _update_forecast_weather(
        self,
        base: WeatherDataOutputData,
        time_of_timestep: datetime,
        time_of_timestep_utc: datetime,
    ) -> WeatherDataOutputData:
        """
        Update the forecast weather data on the given base output.
        Falls back to the last known data on API, data or validation errors.

        Returns the updated output data.
        """
        # base: current data of this timestep + last known forecast data
        output = self._copy_output(
            base,
            forecast_temperature=self.output_data.forecast_temperature,
            forecast_solar=self.output_data.forecast_solar,
        )

        if time_of_timestep < self.next_time_step_forecast_weather:
            logger.debug("Use Weather data of last API_call")
            return output

        logger.debug("Get Forecast Data from Brightsky...")

        try:
            forecast_data = self.get_forecast_weather_data()
        except WeatherDataApiError as e:
            logger.error(f"Error occurred while fetching forecast weather data: {e}")
            forecast_data = None

        if forecast_data is None or not forecast_data.value:
            logger.error("Forecast Weather Data Output is None! Using last data.")
            return output

        temperature_dict = forecast_data.value.get("forecast_temperature", {})
        solar_dict = forecast_data.value.get("forecast_solar", {})

        try:
            output = self._copy_output(
                output,
                forecast_temperature=DataPointDict(
                    value={
                        str(index): value for index, value in temperature_dict.items()
                    },
                    unit=DataUnits.DEGREECELSIUS,
                    time=time_of_timestep_utc,
                ),
                forecast_solar=DataPointDict(
                    value={str(index): value for index, value in solar_dict.items()},
                    unit=DataUnits.B13,
                    time=time_of_timestep_utc,
                ),
            )
        except ValidationError as e:
            logger.error(
                "Validation error while creating WeatherDataOutputData for forecast: "
                f"{e}"
            )
            return output

        # update next time step for forecast weather data retrieval
        self.next_time_step_forecast_weather = self.get_future_time(
            time_of_timestep, self.config_data.time_interval_forecast_weather
        )
        return output

    def calculate(self) -> None:
        """
        Perform the calculations for the WeatherData component
        """
        # check time intervals for current and forecast weather data retrieval
        time_of_timestep = datetime.now(WEATHER_DATA_TZ).replace(microsecond=0)
        time_of_timestep_utc = time_of_timestep.astimezone(timezone.utc)
        logger.debug(f"Current time of timestep: {time_of_timestep}")
        logger.debug(
            "Next time step for current weather data retrieval: "
            f"{self.next_time_step_current_weather}"
        )

        output = WeatherDataOutputData()

        if WeatherApiCallMethod.CURRENT.value in self.unique_weather_types:
            output = self._update_current_weather(
                time_of_timestep, time_of_timestep_utc
            )
        if WeatherApiCallMethod.FORECAST.value in self.unique_weather_types:
            output = self._update_forecast_weather(
                output, time_of_timestep, time_of_timestep_utc
            )

        self.output_data = output
