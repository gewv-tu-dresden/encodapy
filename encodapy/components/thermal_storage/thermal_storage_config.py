"""
Description: Configuration models for the thermal storage component
Author: Martin Altenburger
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from pydantic.functional_validators import model_validator
from encodapy.components.basic_component_config import (
    ComponentValidationError,
    InputData,
    OutputData,
    ConfigData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber, DataPointMedium
from encodapy.utils.mediums import Medium


class TemperatureLimits(BaseModel):
    """
    Configuration of the temperature limits in the termal storage, contains:
        - `minimal_temperature`: Minimal temperature in the thermal storage in °C
        - `maximal_temperature`: Maximal temperature in the thermal storage in °C
        - `reference_temperature`: Reference temperature in the storage in °C (default: 0°C)

    Raises:
        ValueError: if the minimal temperature is heighter than the maximal temperature
    """

    minimal_temperature: float = Field(
        ..., description="Minimal temperature in the thermal storage in °C"
    )
    maximal_temperature: float = Field(
        ..., description="Maximal temperature in the storage in °C"
    )
    reference_temperature: float = Field(
        0, description="Reference temperature in the storage in °C"
    )

    @model_validator(mode="after")
    def check_timerange_parameters(self) -> "TemperatureLimits":
        """Check the timerange parameters.

        Raises:
            ValueError: if the minimal temperature is heighter than the maximal temperature

        Returns:
            TemperatureLimits: The model with the validated parameters
        """

        if self.minimal_temperature > self.maximal_temperature:
            raise ValueError(
                "The minimal temperature should be lower than the maximal temperature"
            )

        return self


class StorageSensorConfig(BaseModel):
    """
    Configuration for the storage sensor in the thermal storage

    Contains:
        `height`: Height of the sensor in percent (0=top, 100=bottom)
        `limits`: Temperature limits for the sensor
    """

    height: float = Field(
        ...,
        ge=0,
        le=100,
        description="Height of the sensor in percent (0=top, 100=bottom)",
    )
    limits: TemperatureLimits


class ThermalStorageTemperatureSensors(BaseModel):
    """
    Configuration for the temperature sensors in the thermal storage

    Contains:
        `storage_sensors`: List of temperature sensors in the thermal storage

    It is required to set at least 3 sensors and no more than 10 sensors. The heights of the sensors
    must be between 0 and 100 percent and in ascending order.

    It is possible to add more information to sensors, thats the reason why this model is used.
    """

    storage_sensors: list[StorageSensorConfig] = Field(
        ..., description="List of temperature sensors (3–10 sensors)"
    )

    @model_validator(mode="after")
    def check_storage_tank_sensors(self) -> "ThermalStorageTemperatureSensors":
        """Check the storage tank sensors:
            - At least 3 sensors are required
            - No more than 10 sensors are allowed
            - Sensor heights must be between 0 and 100 percent
            - Sensor heights must be in ascending order

        Raises:
            ValueError: if the sensors are not set correctly

        Returns:
            ThermalStorageTemperatureSensors: The model with the validated parameters
        """

        if len(self.storage_sensors) < 3:
            raise ValueError("At least 3 storage sensors are required.")
        if len(self.storage_sensors) > 10:
            raise ValueError("No more than 10 storage sensors are allowed.")

        storage_sensor_height_ref = 0.0
        for _, storage_sensor in enumerate(self.storage_sensors):
            if storage_sensor.height < 0.0 or storage_sensor.height > 100.0:
                raise ValueError(
                    "Height of the sensor must be between 0 and 100 percent."
                )
            if storage_sensor.height < storage_sensor_height_ref:
                raise ValueError("Sensor heights must be in ascending order.")
            storage_sensor_height_ref = storage_sensor.height

        return self

    def get_number_of_sensors(self) -> int:
        """
        Get the number of storage sensors configured in the thermal storage.

        Returns:
            int: Number of storage sensors configured.
        """
        return len(self.storage_sensors)


class ThermalStorageInputData(InputData):
    """
    Model for the input of the thermal storage service, containing the temperature sensors
    in the thermal storage.

    The temperature sensors need to be set from 1 to 10, \
        no sensors are allowed to be missing between the others.

    Contains:
        `temperature_1` (DataPointNumber): first temperature sensor
        `temperature_2` (DataPointNumber): second temperature sensor
        `temperature_3` (DataPointNumber): third temperature sensor
        `temperature_4` (Optional[DataPointNumber]): fourth temperature sensor (optional)
        `temperature_5` (Optional[DataPointNumber]): fifth temperature sensor (optional)
        `temperature_6` (Optional[DataPointNumber]): sixth temperature sensor (optional)
        `temperature_7` (Optional[DataPointNumber]): seventh temperature sensor (optional)
        `temperature_8` (Optional[DataPointNumber]): eighth temperature sensor (optional)
        `temperature_9` (Optional[DataPointNumber]): ninth temperature sensor (optional)
        `temperature_10` (Optional[DataPointNumber]): tenth temperature sensor (optional)
        `temperature_in` (Optional[DataPointNumber]): consumer return temperature sensor \
            (optional)
        `temperature_out` (Optional[DataPointNumber]): consumer flow temperature sensor \
            (optional)
    """

    temperature_1: DataPointNumber = Field(
        ...,
        description="Input for the temperature of sensor 1 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_2: DataPointNumber = Field(
        ...,
        description="Input for the temperature of sensor 2 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_3: DataPointNumber = Field(
        ...,
        description="Input for the temperature of sensor 3 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_4: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 4 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_5: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 5 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_6: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 6 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_7: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 7 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_8: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 8 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_9: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 9 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    temperature_10: Optional[DataPointNumber] = Field(
        None,
        description="Input for the temperature of sensor 10 in the thermal storage",
        json_schema_extra={"unit": "CEL"},
    )
    load_temperature_in: Optional[DataPointNumber] = Field(
        None,
        description="Input for the return temperature into the thermal storage (consumer)",
        json_schema_extra={"unit": "CEL"},
    )
    load_temperature_out: Optional[DataPointNumber] = Field(
        None,
        description="Input for the flow temperature from the thermal storage (consumer)",
        json_schema_extra={"unit": "CEL"},
    )

    @model_validator(mode="after")
    def check_storage_temperature_sensors(self) -> "ThermalStorageInputData":
        """
        Check that the storage sensors are configured.
        """
        previous_key = True
        for key, value in self.__dict__.items():
            if key.startswith("temperature") and value is None:
                previous_key = False
            if (
                key.startswith("temperature")
                and value is not None
                and previous_key is False
            ):
                raise ComponentValidationError(
                    f"Temperature sensor {key} is configured, "
                    "but the previous sensor is not configured. "
                    "Please check the configuration."
                )
        return self

    def check_load_connection_sensors(self) -> None:
        """
        Check if the load connection sensors are set

        Raises:
            ValueError: If any of the load connection sensors are not configured.
        """
        if self.load_temperature_in is None:
            raise ComponentValidationError(
                "Load temperature inflow sensor is not configured."
            )
        if self.load_temperature_out is None:
            raise ComponentValidationError(
                "Load temperature outflow sensor is not configured."
            )

    def get_number_storage_sensors(self) -> int:
        """
        Get the number of storage sensors configured in the thermal storage.

        Returns:
            int: Number of storage sensors configured.
        """
        return sum(
            1
            for key, value in self.__dict__.items()
            if key.startswith("temperature") and value is not None
        )


class ThermalStorageOutputData(OutputData):
    """
    Model for the output of the thermal storage service, containing the temperature sensors
    in the thermal storage.

    Each output data point is associated with a specific calculation method, \
        which is defined in the `json_schema_extra` field as `calculation`.

    Contains:
        `storage__level`: Optional[DataPointNumber] : Output for storage charge in percent \
            (0-100) (optional)
        `storage__energy`: Optional[DataPointNumber] : Output for storage energy in Wh (optional)
        `storage__loading_potential_nominal`: Optional[DataPointNumber] : \
            Output for storage loading potential in Wh (optional)
    """

    storage__level: Optional[DataPointNumber] = Field(
        None,
        description="Output for storage charge in percent (0-100)",
        json_schema_extra={"unit": "P1"},
    )
    storage__energy: Optional[DataPointNumber] = Field(
        None,
        description="Output for storage energy in Wh",
        json_schema_extra={"unit": "WHR"},
    )
    storage__loading_potential_nominal: Optional[DataPointNumber] = Field(
        None,
        description="Output for storage loading potential in Wh",
        json_schema_extra={"unit": "WHR"},
    )


class ThermalStorageCalculationMethods(Enum):
    """
    Enum for the calculation methods of the thermal storage service.

    Contains:
        - STATIC_LIMITS: Static limits given by the configuration
        - RETURN_LIMITS: Uses the temperature sensors from the in- and outflow as limits
    """

    STATIC_LIMITS = "static_limits"
    CONNECTION_LIMITS = "connection_limits"


class ThermalStorageEnergyTypes(Enum):
    """
    Enum for the energy types of the thermal storage service.
    
    Contains:
        Nominal ("nominal"): Nominal energy of the thermal storage \
            between the temperature limits
        Minimal ("minimal"): Minimal energy of the thermal storage \
            at the lower temperature limit
        Maximal ("maximal"): Maximal energy of the thermal storage \
            at the upper temperature limit
        Current ("current"): Current energy of the thermal storage \
            based on the current temperatures
    """

    NOMINAL = "nominal"
    MINIMAL = "minimal"
    MAXIMAL = "maximal"
    CURRENT = "current"


class DataPointCalculationMethod(DataPointGeneral):
    """
    Model for datapoints of the controller component which define the calculation method.

    Contains:
        value: The value of the datapoint, which is a string representing the calculation method
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    value: ThermalStorageCalculationMethods


class DataPointSensorConfig(DataPointGeneral):
    """
    Model for datapoints of the controller component which define the sensor configuration.

    Contains:
        value: The value of the datapoint, which is a SensorConfig \
            representing the sensor configuration
        unit: Optional unit of the datapoint, if applicable
        time: Optional timestamp of the datapoint, if applicable
    """

    value: ThermalStorageTemperatureSensors


class ThermalStorageLoadLevelCheck(BaseModel):
    """
    Model for the state of charge check information of the thermal storage service.
    """
    enabled: bool = Field(
        True,
        description="Enable or disable the state of charge check",
    )
    minimal_level: float = Field(
        15.0,
        ge=0,
        le=100,
        description="Minimal share of the upper temperature of charge level in percent (0-100)",
    )
    ref_state_of_charge: float|None = Field(
        None,
        ge=0,
        le=100,
        description="Reference state of charge level in percent (0-100) | set by the process",
    )
class ThermalStorageConfigData(ConfigData):
    """
    Model for the configuration data of the thermal storage service.
    
    Contains:
        `volume`: DataPointNumber : Volume of the thermal storage in m³
        `medium`: DataPointMedium : Medium of the thermal storage
        `sensor_config`: DataPointSensorConfig : \
            Sensor configuration of the thermal storage
        `calculation_method`: DataPointCalculationMethod : \
            Calculation method for the thermal storage
    """

    volume: DataPointNumber = Field(
        ...,
        description="Volume of the thermal storage in m³",
        json_schema_extra={"unit": "MTQ"},
    )
    medium: DataPointMedium = Field(
        DataPointMedium(value=Medium.WATER), description="Medium of the thermal storage"
    )
    sensor_config: DataPointSensorConfig = Field(
        ..., description="Sensor configuration of the thermal storage"
    )
    calculation_method: DataPointCalculationMethod = Field(
        DataPointCalculationMethod(
            value=ThermalStorageCalculationMethods.STATIC_LIMITS
        ),
        description="Calculation method for the thermal storage",
    )
    load_level_check: ThermalStorageLoadLevelCheck = Field(
        ThermalStorageLoadLevelCheck(),
        description="Configuration for the state of charge check",
    )
