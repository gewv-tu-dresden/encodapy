"""
Description: Configuration models for the thermal storage component
Author: Martin Altenburger
"""
from typing import Optional
from pydantic import BaseModel, Field
from pydantic.functional_validators import model_validator
from encodapy.components.components_basic_config import IOAllocationModel

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

class ThermalStorageTemperatureSensors(BaseModel):
    """
    Configuration of the temperature sensors in the termal 
    storage (between 3 and 5 sensors (x = 1...5)), contains:
        - `sensor_x_name`: Name of the sensor
        - `sensor_x_height`: height of the sensor in percent
        - `sensor_x_limits`: Temperature limits of the sensor
        
    Sensor 1 should be the upper sensor in the termal storage and the 
    height is given in percent from the top to the down of the termal storage, 
    so the height of sensor 1 should be the smalest value.
    
    Raises:
        ValueError: if the sensors are not set correctly
    """

    sensor_1_name: str = Field(
        ...,
        description= "Name of the sensor 1 in the termal storage")
    sensor_1_height: float = Field(
        ...,
        description= "Height of the sensor 1 in the termal storage in percent")
    sensor_1_limits: TemperatureLimits

    sensor_2_name: str = Field(
        ...,
        description= "Name of the sensor 2 in the termal storage")
    sensor_2_height: float = Field(
        ...,
        description= "Height of the sensor 2 in the termal storage in percent")
    sensor_2_limits: TemperatureLimits

    sensor_3_name: str = Field(
        ...,
        description= "Name of the sensor 3 in the termal storage")
    sensor_3_height: float = Field(
        ...,
        description= "Height of the sensor 3 in the termal storage in percent")
    sensor_3_limits: TemperatureLimits

    sensor_4_name: Optional[str] = Field(
        None,
        description="Name of the sensor 4 in the termal storage")
    sensor_4_height: Optional[float] = Field(
        None,
        description= "Height of the sensor 4 in the termal storage in percent")
    sensor_4_limits: Optional[TemperatureLimits] = Field(
        None,
        description= "Temperature limits of the sensor 4 in the termal storage")

    sensor_5_name: Optional[str] = Field(
        None,
        description="Name of the sensor 5 in the termal storage")
    sensor_5_height: Optional[float] = Field(
        None,
        description="Height of the sensor 5 in the termal storage in percent")
    sensor_5_limits: Optional[TemperatureLimits] = Field(
        None,
        description= "Temperature limits of the sensor 5 in the termal storage")

    @model_validator(mode="after")
    def check_timerange_parameters(self) -> "ThermalStorageTemperatureSensors":
        """Check the timerange parameters.

        Raises:
            ValueError: if the sensors are not set correctly

        Returns:
            ThermalStorageTemperatureSensors: The model with the validated parameters
        """

        if (self.sensor_1_height > self.sensor_2_height
            or self.sensor_2_height > self.sensor_3_height):
            raise ValueError("Sensor 1 should be the upper sensor in the termal storage "
                             "and the height is given in percent from the top to the down "
                             "of the termal storage, "
                             "so the height of sensor 1 should be the smalest value."
            )

        return self

    @model_validator(mode="after")
    def check_optional_fields(self) -> "ThermalStorageTemperatureSensors":
        """Check the optional fields of the model. If sensor 4 or 5 is set, \
            the height and the limits for this sensor must also be set.

        Raises:
            ValueError: if the optional fields are set incorrectly

        Returns:
            ThermalStorageTemperatureSensors: The model with the validated parameters
        """

        if self.sensor_4_name is not None:
            if self.sensor_4_height is None:
                raise ValueError("If sensor 4 is set, the height must also be set")
            if self.sensor_4_limits is None:
                raise ValueError("If sensor 4 is set, the limits must also be set")

        if self.sensor_5_name is not None:
            if self.sensor_5_height is None:
                raise ValueError("If sensor 5 is set, the height must also be set")
            if self.sensor_5_limits is None:
                raise ValueError("If sensor 5 is set, the limits must also be set")

        return self


class TemperatureSensorValues(BaseModel):
    """
    Model for the temperature sensor values in the thermal storage
    
    Contains:
        `sensor_1` (float): Temperature value of the sensor 1 in the thermal storage in °C
        `sensor_2` (float): Temperature value of the sensor 2 in the thermal storage in °C
        `sensor_3` (float): Temperature value of the sensor 3 in the thermal storage in °C
        `sensor_4` (float, optional): Temperature value of the sensor 4 in the thermal storage in °C
        `sensor_5` (float, optional): Temperature value of the sensor 5 in the thermal storage in °C
    """

    sensor_1: float = Field(
        ...,
        description= "Temperature value of the sensor 1 in the thermal storage in °C")
    sensor_2: float = Field(
        ...,
        description= "Temperature value of the sensor 2 in the thermal storage in °C")
    sensor_3: float = Field(
        ...,
        description= "Temperature value of the sensor 3 in the thermal storage in °C")
    sensor_4: Optional[float] = Field(
        None,
        description= "Temperature value of the sensor 4 in the thermal storage in °C")
    sensor_5: Optional[float] = Field(
        None,
        description= "Temperature value of the sensor 5 in the thermal storage in °C")

class InputModel(BaseModel):
    """
    Model for the input of the thermal storage service, containing the temperature sensors
    in the thermal storage.
    
    Contains:
        `temperature_1`: IOAllocationModel = first temperature sensor
        `temperature_2`: IOAllocationModel = second temperature sensor
        `temperature_3`: IOAllocationModel = third temperature sensor
        `temperature_4`: Optional[IOAllocationModel] = fourth temperature sensor (optional)
        `temperature_5`: Optional[IOAllocationModel] = fifth temperature sensor (optional)
    """
    temperature_1: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 1 in the thermal storage")
    temperature_2: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 2 in the thermal storage")
    temperature_3: IOAllocationModel = Field(
        ...,
        description="Input for the temperature of sensor 3 in the thermal storage")
    temperature_4: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 4 in the thermal storage")
    temperature_5: Optional[IOAllocationModel] = Field(
        None,
        description="Input for the temperature of sensor 5 in the thermal storage")

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
