"""
Description: Configuration models for the thermal storage component
Author: Martin Altenburger
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from pydantic.functional_validators import model_validator
from encodapy.components.components_basic_config import IOAllocationModel, ComponentValidationError

class TemperatureLimits(BaseModel):
    """
    Configuration of the temperature limits in the termal storage, contains:
        - `minimal_temperature`: Minimal temperature in the thermal storage in °C
        - `maximal_temperature`: Maximal temperature in the thermal storage in °C
        
    Raises:
        ValueError: if the minimal temperature is heighter than the maximal temperature
    """
    minimal_temperature: float = Field(
        ...,
        description="Minimal temperature in the thermal storage in °C")
    maximal_temperature: float = Field(
        ...,
        description="Maximal temperature in the storage in °C")
    reference_temperature: float = Field(
        0,
        description="Reference temperature in the storage in °C")

    @model_validator(mode="after")
    def check_timerange_parameters(self) -> "TemperatureLimits":
        """Check the timerange parameters.

        Raises:
            ValueError: if the minimal temperature is heighter than the maximal temperature

        Returns:
            TemperatureLimits: The model with the validated parameters
        """

        if self.minimal_temperature > self.maximal_temperature :
            raise ValueError("The minimal temperature should be lower than the maximal temperature")

        return self

class StorageSensorConfig(BaseModel):
    """
    Configuration for the storage sensor in the thermal storage

    Contains:
        `name`: Name of the sensor in the thermal storage
        `height`: Height of the sensor in percent (0=top, 100=bottom)
        `limits`: Temperature limits for the sensor
    """
    # name: str = Field(..., description="Name of the sensor in the thermal storage")
    height: float = Field(..., ge=0, le=100,
                          description="Height of the sensor in percent (0=top, 100=bottom)")
    limits: TemperatureLimits

class ConnectionSensorConfig(BaseModel):
    """
    Configuration for the connection sensor in the thermal storage
    
    Contains:
        `name`: Name of the thermal sensor on the connection (heat demand)
    """
    name: str = Field(...,
                      description="Name of the thermal sensor on the connection (heat demand)")

class ThermalStorageTemperatureSensors(BaseModel):
    """
    Configuration for the temperature sensors in the thermal storage
    
    Contains:
        `storage_sensors`: List of temperature sensors in the thermal storage
        `load_connection_sensor_out`: Thermal sensor on the load connection \
            outflow from thermal storage
        `load_connection_sensor_in`: Thermal sensor on the load connection \
            inflow to thermal storage
    """

    storage_sensors: list[StorageSensorConfig] = Field(
        ...,
        description="List of temperature sensors (3–10 sensors)")
    load_connection_sensor_out: Optional[ConnectionSensorConfig] = Field(
        None,
        description="Thermal sensor on the load connection, outflow from thermal storage")
    load_connection_sensor_in: Optional[ConnectionSensorConfig] = Field(
        None,
        description="Thermal sensor on the load connection, inflow to thermal storage")

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
        for storage_sensor in self.storage_sensors: # pylint: disable=E1133
            if storage_sensor.height < 0.0 or storage_sensor.height > 100.0:
                raise ValueError("Height of the sensor must be between 0 and 100 percent.")
            if storage_sensor.height < storage_sensor_height_ref:
                raise ValueError("Sensor heights must be in ascending order.")
            storage_sensor_height_ref = storage_sensor.height

        return self

    def check_connection_sensors(self) -> None:
        """
        TODO use this
        Check the connection sensors:
            - If they are needed, they must have a name

        Raises:
            ValueError: if the connection sensors are not set correctly
        """

        if self.load_connection_sensor_out is None:
            raise ComponentValidationError("The load connection sensor outflow must have a name.")
        if self.load_connection_sensor_in is None:
            raise ComponentValidationError("The load connection sensor inflow must have a name.")


class TemperatureSensorValues(BaseModel):
    """
    Model for the temperature sensor values in the thermal storage
    
    Contains:
        `storage_sensors` (list[float]): \
            Temperature values of the storage sensors in the thermal storage
        `load_temperature_in` (Optional[float]): \
            Temperature value of the load connection sensor inflow
        `load_temperature_out` (Optional[float]): \
            Temperature value of the load connection sensor outflow
    """

    storage_sensors: list[float] = Field(
        ...,
        description="Temperature values of the storage sensors in the thermal storage in °C")
    load_temperature_in: Optional[float] = Field(
        ...,
        description="Temperature value of the load connection sensor inflow in °C")
    load_temperature_out: Optional[float] = Field(
        ...,
        description="Temperature value of the load connection sensor outflow in °C")

    def check_connection_sensors(self):
        """
        Check the connection sensors for availability.
        """
        if self.load_temperature_in is None:
            raise ComponentValidationError("The load connection sensor inflow must be available.")
        if self.load_temperature_out is None:
            raise ComponentValidationError("The load connection sensor outflow must be available.")

class InputModel(BaseModel):
    """
    Model for the input of the thermal storage service, containing the temperature sensors
    in the thermal storage.

    The temperature sensors need to be set from 1 to 10, \
        no sensors are allowed to be missing between the others.

    Contains:
        `temperature_1` (IOAllocationModel): first temperature sensor
        `temperature_2` (IOAllocationModel): second temperature sensor
        `temperature_3` (IOAllocationModel): third temperature sensor
        `temperature_4` (Optional[IOAllocationModel]): fourth temperature sensor (optional)
        `temperature_5` (Optional[IOAllocationModel]): fifth temperature sensor (optional)
        `temperature_6` (Optional[IOAllocationModel]): sixth temperature sensor (optional)
        `temperature_7` (Optional[IOAllocationModel]): seventh temperature sensor (optional)
        `temperature_8` (Optional[IOAllocationModel]): eighth temperature sensor (optional)
        `temperature_9` (Optional[IOAllocationModel]): ninth temperature sensor (optional)
        `temperature_10` (Optional[IOAllocationModel]): tenth temperature sensor (optional)
        `temperature_in` (Optional[IOAllocationModel]): consumer return temperature sensor \
            (optional)
        `temperature_out` (Optional[IOAllocationModel]): consumer flow temperature sensor \
            (optional)
    """
    temperature_1: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 1 in the thermal storage"
    )
    temperature_2: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 2 in the thermal storage"
    )
    temperature_3: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 3 in the thermal storage"
    )
    temperature_4: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 4 in the thermal storage"
    )
    temperature_5: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 5 in the thermal storage"
    )
    temperature_6: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 6 in the thermal storage"
    )
    temperature_7: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 7 in the thermal storage"
    )
    temperature_8: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 8 in the thermal storage"
    )
    temperature_9: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 9 in the thermal storage"
    )
    temperature_10: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 10 in the thermal storage"
    )
    load_temperature_in: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the return temperature into the thermal storage (consumer)"
    )
    load_temperature_out: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the flow temperature from the thermal storage (consumer)"
    )

    @model_validator(mode="after")
    def check_storage_temperature_sensors(self) -> "InputModel":
        """
        Check that the storage sensors are configured.
        """
        previous_key = True
        for key, value in self.__dict__.items():
            if key.startswith("temperature") and value is None:
                previous_key = False
            if key.startswith("temperature") and value is not None and previous_key is False:
                raise ComponentValidationError(f"Temperature sensor {key} is configured, "
                                               "but the previous sensor is not configured. "
                                               "Please check the configuration.")
        return self

    def check_load_connection_sensors(self) -> None:
        """
        Check if the load connection sensors are set
        
        Raises:
            ValueError: If any of the load connection sensors are not configured.
        """
        if self.load_temperature_in is None:
            raise ComponentValidationError("Load temperature inflow sensor is not configured.")
        if self.load_temperature_out is None:
            raise ComponentValidationError("Load temperature outflow sensor is not configured.")

    def get_number_storage_sensors(self) -> int:
        """
        Get the number of storage sensors configured in the thermal storage.

        Returns:
            int: Number of storage sensors configured.
        """
        return sum(1 for key, value in self.__dict__.items()
                   if key.startswith("temperature") and value is not None)

class OutputModel(BaseModel):
    """
    Model for the output of the thermal storage service, containing the temperature sensors
    in the thermal storage.
    
    Contains:
        `storage__level`: Optional[IOAllocationModel] = Output for storage charge in percent \
            (0-100) (optional)
        `storage__energy`: Optional[IOAllocationModel] = Output for storage energy in kWh \
            (optional)
    """
    storage__level: Optional[IOAllocationModel] = Field(
        None,
        description="Output for storage charge in percent (0-100)")
    storage__energy: Optional[IOAllocationModel] = Field(
        None,
        description="Output for storage energy in Wh")

class ThermalStorageIO(BaseModel):
    """
    Model for the input and output of the thermal storage service.
    
    Contains:
        `input`: InputModel = Input configuration for the thermal storage service
        `output`: OutputModel = Output configuration for the thermal storage service
    """
    input: InputModel = Field(
        ...,
        description="Input configuration for the thermal storage service")
    output: OutputModel = Field(
        ...,
        description="Output configuration for the thermal storage service")

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
