"""
Simple Method to caluculate the energy in a the thermal storage
Author: Martin Altenburger
"""
from typing import Union, Optional
from pandas import DataFrame, Series
import numpy as np
from loguru import logger
from pydantic import ValidationError
from encodapy.components.thermal_storage_config import (
    ThermalStorageTemperatureSensors,
    TemperatureLimits,
    TemperatureSensorValues,
    InputModel,
    OutputModel,
    ThermalStorageIO)
from encodapy.utils.mediums import(
    Medium,
    get_medium_parameter)
from encodapy.config.models import ControllerComponentModel

class ThermalStorage:
    """
    Class to calculate the energy in a thermal storage.
    
    Args:
        sensor_config (ThermalStorageTemperatureSensors): \
            Configuration of the temperature sensors in the thermal storage
        volume (float): Volume of the thermal storage in m³
        medium (Medium): Medium in the thermal storage, e.g. water 
    
    """
    def __init__(self,
                 config: ControllerComponentModel
                 ) -> None:
        # Basic initialization of the thermal storage
        self.sensor_config: ThermalStorageTemperatureSensors = None
        self.medium: Medium = None
        self.volume: float = None
        self.io_model: ThermalStorageIO = None

        # Prepare the thermal storage based on the configuration
        self.prepare_start_thermal_storage(config=config)
        self.sensor_volumes = self._calculate_volume_per_sensor()
        self.sensor_values = None


    def _calculate_volume_per_sensor(self) -> dict:
        """
        Function to calculate the volume per sensor in the thermal storage

        Returns:
            dict: Volume per sensor in the thermal storage in m³
        """
        sensor_names = []
        sensor_heights = []

        sensor_volumes = {}

        old_height = 0
        for field_name, value in self.sensor_config:

            if "name" in field_name and value is not None:
                sensor_names.append(value)

            elif "height" in field_name and value is not None:
                sensor_heights.append(value)

        old_height = 0
        for index, sensor in enumerate(sensor_names):
            if index == len(sensor_names)-1:
                new_height = 100
            else:
                new_height = (sensor_heights[index] + sensor_heights[index+1])/2

            sensor_volumes[sensor] = (new_height - old_height)/100 * self.volume

            old_height = new_height


        return sensor_volumes

    def _get_sensor_volume(self,
                           sensor:str) -> float:
        """
        Function to get the volume of the sensors in the thermal storage

        Returns:
            float: Volume of the sensors in the thermal storage in m³
        """

        return round(self.sensor_volumes[sensor],3)

    def _get_sensor_limits(self,
                           sensor:str) -> TemperatureLimits:
        """
        Function to get the temperature limits of the sensors in the thermal storage
        Args:
            sensor (str): Name of the sensor in the thermal storage
        Returns:
            TemperatureLimits: Temperature limits of the sensors in the thermal storage
        """
        sensor_id = str(sensor.split("_")[1])

        for field_name, value in self.sensor_config:

            if "limits" in field_name and value is not None and sensor_id in field_name:
                return value

        return None

    def get_nominal_energy_content(self
                                   ) -> float:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            float: Nominal energy content of the thermal storage in Wh
        """

        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue
            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.maximal_temperature
                                        - limits.minimal_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)

    def get_storage_energy_minimum(self) -> float:
        """
        Function to get the minimum energy content of the thermal storage

        Returns:
            float: Minimum energy content of the thermal storage in Wh
        """

        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue
            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.minimal_temperature
                                        - limits.reference_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)

    def get_storage_energy_maximum(self) -> float:
        """
        Function to get the maximum energy content of the thermal storage

        Returns:
            float: Maximum energy content of the thermal storage in Wh
        """
        medium_parameter = get_medium_parameter(medium = self.medium)

        total_energy_calculator = 0
        for i in range(1, 6):
            sensor_name = getattr(self.sensor_config, f"sensor_{i}_name")

            if sensor_name is None:
                continue

            limits = self._get_sensor_limits(sensor_name)

            total_energy_calculator += ((limits.maximal_temperature
                                        - limits.reference_temperature)
                                        * self._get_sensor_volume(sensor_name))

        return round(total_energy_calculator
                * medium_parameter.rho
                * medium_parameter.cp
                /3.6,2)

    def set_temperature_values(self,
                               temperature_values: dict
                               ) -> None:
        """
        Function to set the sensor values in the thermal storage

        Args:
            sensor_values (dict): Sensor values in the thermal storage \
                with the sensor names as keys
        """

        self.sensor_values = TemperatureSensorValues(
            sensor_1=temperature_values[self.sensor_config.sensor_1_name],
            sensor_2=temperature_values[self.sensor_config.sensor_1_name],
            sensor_3=temperature_values[self.sensor_config.sensor_1_name],
            sensor_4=temperature_values[self.sensor_config.sensor_4_name]
            if self.sensor_config.sensor_4_name is not None else None,
            sensor_5=temperature_values[self.sensor_config.sensor_5_name]
            if self.sensor_config.sensor_5_name is not None else None)

    def check_temperatur_of_highest_sensor(self,
                                           df:DataFrame,
                                           sensor_name:str,
                                           temperature_limits:TemperatureLimits,
                                           )-> Series:
        """
        Function to check if the temperature of the highest sensor is too low, \
            so there is no energy left
        Args:
            df (pd.DataFrame): DataFrame with temperature values and state of charge
            sensor_name (str): Name of the highest sensor / column in the dataframe
            temperature_limits (TemperatureLimits): Temperature Limits of the sensor

        Returns:
            pd.Series: Adjustested state of charge
        """
        ref_value = (
            temperature_limits.minimal_temperature
            + (temperature_limits.maximal_temperature  - temperature_limits.minimal_temperature
               ) * 0.1)
        df = df.copy()

        df["state_of_charge"] = np.where(
            df[sensor_name] < temperature_limits.minimal_temperature , 0,
            np.where(df[sensor_name] < ref_value,
                     (df[sensor_name] - temperature_limits.minimal_temperature )
                     /(temperature_limits.maximal_temperature
                       -temperature_limits.minimal_temperature),
                     df["state_of_charge"]))

        return df["state_of_charge"]

    def calculate_state_of_charge(self,
                                  input_data: Optional[Union[dict,
                                                             DataFrame,
                                                             TemperatureSensorValues
                                                             ]] = None
                                  )-> Union[float, DataFrame]:
        """
        Function to calculate the state of charge of the thermal storage

        If the temperature of the highest sensor is too low, there is no energy left.
        
        Args:
            input_data (Optional[Union[dict, DataFrame, TemperatureSensorValues]]): \
                Input data for the calculation of the state of charge of the thermal storage \
                    (temperature values of the sensors)

        Returns:
            Union[float, DataFrame]: State of charge of the thermal storage in percent (0-100) 
                / DataFrame with the state of charge if the input is a DataFrame
        """

        if input_data is None:
            input_data = self.sensor_values

        if isinstance(input_data, dict):
            df = DataFrame(input_data, index=[0])


        elif isinstance(input_data, TemperatureSensorValues):
            input_data_dict = {}
            for i in range (1, len(input_data.model_dump().keys()) + 1):
                input_data_dict[self.sensor_config.model_dump()
                                [f"sensor_{i}_name"]
                                ] = input_data.model_dump()[f"sensor_{i}"]

            df = DataFrame(input_data_dict, index=[0])

        else:
            df = input_data.copy()


        sensors = {}
        sensor_limits = {}
        for field_name, value in self.sensor_config:

            if "name" in field_name and value is not None:
                sensors[value] = self._get_sensor_volume(value)
                sensor_limits[value] = self._get_sensor_limits(field_name)

        df["state_of_charge"] = 0

        for sensor_name, sensor_volume in sensors.items():

            df["state_of_charge"] += ((df[sensor_name]
                                       - sensor_limits[sensor_name].minimal_temperature)
                                      /(sensor_limits[sensor_name].maximal_temperature
                                        - sensor_limits[sensor_name].minimal_temperature)
                                      * sensor_volume)

        df["state_of_charge"] = (df["state_of_charge"] / self.volume * 100).clip(lower=0)

        df["state_of_charge"]  = self.check_temperatur_of_highest_sensor(
            df = df,
            sensor_name=self.sensor_config.sensor_1_name,
            temperature_limits=sensor_limits[self.sensor_config.sensor_1_name]
        )

        if isinstance(input_data, (dict, TemperatureSensorValues)):
            return round(df["state_of_charge"].values[0],2)

        return df.filter(["state_of_charge"]).round(2)

    def get_energy_content(self,
                           state_of_charge: Union[float, None] = None
                           ) -> float:
        """
        Function to calculate the energy content of the thermal storage

        Args:
            state_of_charge (float): State of charge of the thermal storage in percent (0-100)

        Returns:
            float: Energy content of the thermal storage in Wh
        """
        if state_of_charge is None:
            if self.sensor_values is None:
                raise ValueError("Sensor values are not set. Please set the sensor values first")
            state_of_charge = self.calculate_state_of_charge(input_data = self.sensor_values)

        return round(state_of_charge/100
                * self.get_nominal_energy_content(),2)

    def _prepare_thermal_storage(self,
                                 config:ControllerComponentModel
                                 ):
        """
        Function to prepare the thermal storage based on the configuration.

        Args:
            config (ControllerComponentModel): Configuration of the thermal storage component

        Raises:
            KeyError: Invalid medium in the configuration
            KeyError: No volume of the thermal storage specified in the configuration
            KeyError: No sensor configuration of the thermal storage specified in the configuration
            ValidationError: Invalid sensor configuration for the thermal storage

        Returns:
            ThermalStorage: Instance of the ThermalStorage class with the prepared configuration
        """

        medium_value = config.config.get("medium")
        if medium_value is None:
            error_msg = "No medium of the thermal storage specified in the configuration, \
                using default medium 'water'"
            logger.warning(error_msg)
            medium_value = 'water'
        try:
            self.medium:Medium = Medium(medium_value)
        except ValueError:
            error_msg = f"Invalid medium in the configuration: '{medium_value}'"
            logger.error(error_msg)
            raise ValueError(error_msg) from None

        self.volume:float = config.config.get("volume")

        if self.volume is None:
            error_msg = "No volume of the thermal storage specified in the configuration."
            logger.error(error_msg)
            raise KeyError(error_msg) from None

        sensor_config = config.config.get("sensor_config")
        if sensor_config is None:
            error_msg = "No sensor configuration of the thermal storage specified \
                in the configuration."
            logger.error(error_msg)
            raise KeyError(error_msg) from None

        try:
            self.sensor_config = ThermalStorageTemperatureSensors.model_validate(sensor_config)
        except ValidationError:
            error_msg = "Invalid sensor configuration in the thermal storage"
            logger.error(error_msg)
            raise

    def _prepare_i_o_config(self,
                            config:ControllerComponentModel
                            ):
        """
        Function to prepare the inputs and outputs of the service.
        This function is called before the service is started.
        """
        try:
            input_config = InputModel.model_validate(config.inputs)
        except ValidationError:
            error_msg = "Invalid input configuration for the thermal storage"
            logger.error(error_msg)
            raise

        try:
            output_config = OutputModel.model_validate(config.outputs)
        except ValidationError :
            error_msg = "Invalid output configuration for the thermal storage"
            logger.error(error_msg)
            raise

        self.io_model = ThermalStorageIO(
            input=input_config,
            output=output_config
            )

    def _check_input_configuration(self):
        """
        Function to check the input configuration of the service \
            in comparison to the sensor configuration.
        The inputs needs to match the sensor configuration.
        Raises:
            KeyError: If the input configuration does not match the sensor configuration
            Warning: If the input configuration does not match the sensor configuration,\
                but is not critical
        """
        # pylint problems see: https://github.com/pylint-dev/pylint/issues/4899
        if (self.sensor_config.sensor_4_name is not None
            and self.io_model.input.temperature_4 is None): # pylint: disable=no-member
            error_msg = ("Input configuration does not match sensor configuration: "
                         "Sensor 4 is defined in the sensor configuration, "
                         "but not in the input configuration.")
            logger.error(error_msg)
            raise KeyError(error_msg)
        if (self.sensor_config.sensor_5_name is not None
            and self.io_model.input.temperature_5 is None): # pylint: disable=no-member
            error_msg = ("Input configuration does not match sensor configuration: "
                         "Sensor 5 is defined in the sensor configuration, "
                         "but not in the input configuration.")
            logger.error(error_msg)
            raise KeyError(error_msg)

        if (self.sensor_config.sensor_4_name is None
            and self.io_model.input.temperature_4 is not None): # pylint: disable=no-member
            logger.warning("Input configuration does not match sensor configuration: "
                           "Sensor 4 is defined in the input configuration, "
                           "but not in the sensor configuration."
                           "The sensor will not be used in the calculation.")
        if (self.sensor_config.sensor_5_name is None
            and self.io_model.input.temperature_5 is not None): # pylint: disable=no-member
            logger.warning("Input configuration does not match sensor configuration: "
                           "Sensor 5 is defined in the input configuration, "
                           "but not in the sensor configuration."
                           "The sensor will not be used in the calculation.")


    def prepare_start_thermal_storage(
        self,
        config: ControllerComponentModel
        ):
        """
        Function to prepare the start of the service, \
            including the loading configuration of the service \
                and preparing the thermal storage.
        """

        self._prepare_thermal_storage(config=config)

        self._prepare_i_o_config(config=config)

        self._check_input_configuration()
