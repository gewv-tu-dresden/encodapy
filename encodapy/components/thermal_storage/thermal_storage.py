"""
Simple Method to caluculate the energy in a the thermal storage
Author: Martin Altenburger, Paul Seidel
"""
from typing import Union, Optional
from loguru import logger
from pydantic import ValidationError
from encodapy.components.thermal_storage.thermal_storage_config import (
    ThermalStorageTemperatureSensors,
    TemperatureLimits,
    TemperatureSensorValues,
    InputModel,
    OutputModel,
    ThermalStorageIO,
    ThermalStorageCalculationMethods,
    ThermalStorageEnergyTypes)
from encodapy.components.basic_component import BasicComponent
from encodapy.components.components_basic_config import IOModell, ComponentValidationError
from encodapy.utils.mediums import(
    Medium,
    get_medium_parameter)
from encodapy.utils.models import StaticDataEntityModel, InputDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.units import DataUnits

class ThermalStorage(BasicComponent):
    """
    Class to calculate the energy in a thermal storage.

    Service needs to be prepared before use (`prepare_start_thermal_storage`).

    Args:
        sensor_config (ThermalStorageTemperatureSensors): \
            Configuration of the temperature sensors in the thermal storage,
            Calculation method
        statc data of the ThermalStorage
        component_id (str): ID of the thermal storage component
    
    
    """
    def __init__(self,
                 config: Union[ControllerComponentModel, list[ControllerComponentModel]],
                 component_id: str,
                 static_data: Optional[list[StaticDataEntityModel]] = None,
                 ) -> None:

        super().__init__(config=config,
                         component_id=component_id,
                         static_data=static_data)


        # Basic initialization of the thermal storage
        # Configuration of the thermal storage
        self.sensor_config: Optional[ThermalStorageTemperatureSensors] = None
        self.medium: Optional[Medium] = None
        self.volume: Optional[float] = None
        # Variables for the calcuation
        self.io_model: Optional[ThermalStorageIO] = None
        self.sensor_values: Optional[TemperatureSensorValues] = None
        self.sensor_volumes: Optional[dict] = None
        self.calculation_method: ThermalStorageCalculationMethods = (
            ThermalStorageCalculationMethods.STATIC_LIMITS)

        # Prepare the thermal storage
        self.prepare_start_thermal_storage()


    def thermal_storage_usable(self)-> bool:
        """
        Check that the thermal storage component has been configured and is ready to use.

        Returns:
            bool: True if the thermal storage is usable, False otherwise.
        """
        if self.sensor_config is None:
            return False
        if self.sensor_volumes is None:
            return False
        if self.medium is None:
            return False
        return True

    def _calculate_volume_per_sensor(self) -> dict:
        """
        Function to calculate the volume per sensor in the thermal storage

        Returns:
            dict: Volume per sensor in the thermal storage in m³
        """

        sensor_volumes = {}

        if self.sensor_config is None:
            raise ValueError("Sensor configuration is not set.")
        if self.volume is None:
            raise ValueError("Volume of the thermal storage is not set.")

        sensor_height_ref = 0.0

        for index, storage_sensor in enumerate(self.sensor_config.storage_sensors):

            if index == len(self.sensor_config.storage_sensors) - 1:
                sensor_height_new = 100.0
            else:
                sensor_height_new = (storage_sensor.height
                                     + self.sensor_config.storage_sensors[index + 1].height) / 2

            sensor_volumes[index] = (sensor_height_new - sensor_height_ref)/100 * self.volume
            sensor_height_ref = sensor_height_new

        return sensor_volumes

    def _get_sensor_volume(self,
                           sensor:int) -> float:
        """
        Function to get the volume of the sensors in the thermal storage

        Returns:
            float: Volume of the sensors in the thermal storage in m³
        """
        if self.sensor_volumes is None:
            raise ValueError("Sensor volumes are not set.")
        if sensor not in self.sensor_volumes:
            raise ValueError(f"Sensor {sensor} is not configured.")

        return round(self.sensor_volumes[sensor],3)

    def _get_connection_limits(self,
                               sensor_id: int,
                               config_limits:TemperatureLimits
                               ) -> TemperatureLimits:
        """
        Function to get the connection limits of the sensors in the thermal storage:
            - Uses the actual temperature of the outlet sensor (heat demand) as \
                minimal temperature of the upper storage temperature
            - Uses the actual temperature of the inlet sensor (heat demand) as \
                minimal temperature of the lower storage temperature
        Args:
            sensor_id (str): ID of the sensor in the thermal storage
        Returns:
            TemperatureLimits: Temperature limits of the sensors in the thermal storage
        """
        if self.sensor_config is None:
            raise ValueError("Sensor configuration is not set.")
        if self.sensor_values is None:
            raise ValueError("Sensor values are not set.")

        if self.sensor_values.load_temperature_out is None:
            logger.warning("Load temperature outflow is not set.")
            return config_limits
        if self.sensor_values.load_temperature_in is None:
            logger.warning("Load temperature inflow is not set.")
            return config_limits

        if sensor_id == 0:
            return TemperatureLimits(
                minimal_temperature=self.sensor_values.load_temperature_out,
                maximal_temperature=config_limits.maximal_temperature,
                reference_temperature= config_limits.reference_temperature
            )

        return TemperatureLimits(
                minimal_temperature=self.sensor_values.load_temperature_in,
                maximal_temperature=config_limits.maximal_temperature,
                reference_temperature= config_limits.reference_temperature
            )


    def _get_sensor_limits(self,
                           sensor_id:int) -> TemperatureLimits:
        """
        Function to get the temperature limits of the sensors in the thermal storage
        Args:
            sensor (str): Name of the sensor in the thermal storage #TODO
        Returns:
            TemperatureLimits: Temperature limits of the sensors in the thermal storage
        """

        if self.sensor_config is None:
            raise ValueError("Sensor configuration is not set.")

        config_limits = self.sensor_config.storage_sensors[sensor_id].limits

        if self.calculation_method == ThermalStorageCalculationMethods.STATIC_LIMITS:
            return config_limits

        if self.calculation_method == ThermalStorageCalculationMethods.CONNECTION_LIMITS:

            limits = self._get_connection_limits(sensor_id = sensor_id,
                                                config_limits= config_limits)

            return limits

        logger.warning(f"Unknown calculation method: {self.calculation_method}")

        return config_limits

    def get_storage_energy_content(self,
                                   energy_type: ThermalStorageEnergyTypes
                                   ) -> float:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            float: Nominal energy content of the thermal storage in Wh
        """
        # Check if the calculation is possible
        if self.sensor_config is None:
            raise ValueError("Sensor configuration is not set.")
        if self.medium is None:
            raise ValueError("Medium is not set.")
        if self.sensor_volumes is None:
            raise ValueError("Sensor volumes are not set.")
        if self.sensor_values is None:
            raise ValueError("Sensor values are not set.")

        nominal_energy = 0

        for index, _ in enumerate(self.sensor_config.storage_sensors):
            medium_parameter = get_medium_parameter(
                medium = self.medium,
                temperature=self.sensor_values.storage_sensors[index]) # pylint: disable=E1136

            sensor_limits = self._get_sensor_limits(sensor_id=index)

            if energy_type is ThermalStorageEnergyTypes.NOMINAL:
                temperature_difference = (sensor_limits.maximal_temperature
                            - sensor_limits.minimal_temperature)

            elif energy_type is ThermalStorageEnergyTypes.MINIMAL:
                temperature_difference = (sensor_limits.minimal_temperature
                            - sensor_limits.reference_temperature)

            elif energy_type is ThermalStorageEnergyTypes.MAXIMAL:
                temperature_difference = (sensor_limits.maximal_temperature
                            - sensor_limits.reference_temperature)

            elif energy_type is ThermalStorageEnergyTypes.CURRENT:
                temperature_difference = (self.sensor_values.storage_sensors[index]  # pylint: disable=E1136
                            - sensor_limits.minimal_temperature)

            else:
                raise ValueError(f"Unknown energy type: {energy_type}")

            nominal_energy += (temperature_difference
                            * self.sensor_volumes[index]
                            * medium_parameter.rho
                            * medium_parameter.cp
                            / 3.6)

        return round(nominal_energy, 2)

    def get_storage_energy_nominal(self
                                   ) -> float:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            float: Nominal energy content of the thermal storage in Wh
        """

        return self.get_storage_energy_content(ThermalStorageEnergyTypes.NOMINAL)

    def get_storage_energy_minimum(self) -> float:
        """
        Function to get the minimum energy content of the thermal storage

        Returns:
            float: Minimum energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return self.get_storage_energy_content(ThermalStorageEnergyTypes.MINIMAL)

    def get_storage_energy_maximum(self) -> float:
        """
        Function to get the maximum energy content of the thermal storage

        Returns:
            float: Maximum energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return self.get_storage_energy_content(ThermalStorageEnergyTypes.MAXIMAL)

    def get_storage_energy_current(self) -> float:
        """
        Function to get the current energy content of the thermal storage

        Returns:
            float: Current energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return self.get_storage_energy_content(ThermalStorageEnergyTypes.CURRENT)

    def set_temperature_values(self,
                               input_entities: list[InputDataEntityModel]
                               ) -> None:
        """
        Function to set the sensor values in the thermal storage

        Args:
            input_entities (list[InputDataEntityModel]): Input entities with temperature values
        Raises:
            ValueError: If the thermal storage is not usable or \
                the sensor values are not set correctly
        TODO: check the unit?
        """
        if self.thermal_storage_usable() is False:
            raise ValueError(
                "Thermal storage is not usable. "
                "Please prepare the thermal storage first."
                )

        if self.io_model is None:
            raise ValueError("IO model is not set.")

        # Temperature values, which are not sensors in the thermal storage:
        # TemperatureSensorValues.load_temperature_in / .load_temperature_out
        temperature_values = {}
        # Temperature values from the inside - TemperatureSensorValues.storage_sensors
        storage_temperatures = []

        for key, datapoint_information in self.io_model.input.__dict__.items():
            if datapoint_information is None:
                continue

            temperature_value, _temperature_unit = self.get_component_input(
                    input_entities=input_entities,
                    input_config=datapoint_information
                )
            if not isinstance(temperature_value, (str, int, float)):
                logger.error(f"Invalid temperature value for {key}: {temperature_value} "
                             "Sensor Values are not set correctly")
                return

            if key.startswith("temperature_"):
                storage_temperatures.append(float(temperature_value))
            else:
                temperature_values[key] = float(temperature_value)

        self.sensor_values = TemperatureSensorValues(
            storage_sensors= storage_temperatures,
            load_temperature_in= temperature_values.get("load_temperature_in", None),
            load_temperature_out= temperature_values.get("load_temperature_out", None)
        )

        if self.calculation_method is ThermalStorageCalculationMethods.CONNECTION_LIMITS:
            self.sensor_values.check_connection_sensors()

    def _check_temperatur_of_highest_sensor(self,
                                            state_of_charge: float)-> float:
        """
        Function to check if the temperature of the highest sensor is too low, \
            so there is no energy left
        Args:
            state_of_charge (float): Current state of charge

        Returns:
            float: Adjusted state of charge
        """
        if self.sensor_values is None:
            logger.error("Sensor values are not set. Please set the sensor values first")
            return state_of_charge

        temperature_limits = self._get_sensor_limits(sensor_id=0)
        ref_value = (
            temperature_limits.minimal_temperature
            + (temperature_limits.maximal_temperature - temperature_limits.minimal_temperature)
            * 0.1)

        if self.sensor_values.storage_sensors[0] < temperature_limits.minimal_temperature:  # pylint: disable=E1136
            return 0
        if self.sensor_values.storage_sensors[0] < ref_value:  # pylint: disable=E1136
            return ((self.sensor_values.storage_sensors[0]  # pylint: disable=E1136
                     - temperature_limits.minimal_temperature)
                    /(temperature_limits.maximal_temperature
                      - temperature_limits.minimal_temperature))

        return state_of_charge

    def calculate_state_of_charge(self)-> float:
        """
        Function to calculate the state of charge of the thermal storage

        If the temperature of the highest sensor is too low, there is no energy left, \
            so the state of charge is 0.

        Returns:
            float: State of charge of the thermal storage in percent (0-100)
        """

        state_of_charge = (self.get_storage_energy_current()
                           / self.get_storage_energy_nominal()
                           * 100)

        state_of_charge = self._check_temperatur_of_highest_sensor(state_of_charge=state_of_charge)

        return round(state_of_charge,2)

    def _prepare_thermal_storage(self,
                                 )-> None:
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

        if self.component_config.staticdata is None:
            logger.error("Static data of the thermal storage is missing in the configuration. "
                         "Please check the configuration.")
            return
        if len(self.static_data.root.keys()) < len(self.component_config.staticdata.root.keys()):
            logger.error("Static data of the thermal storage is not complete. "
                         "Please check the configuration.")
            return

        medium_value = self.get_component_static_data(
            component_id="medium"
        )
        if not isinstance(medium_value, str):
            error_msg = "No medium of the thermal storage specified in the configuration, \
                or wrong type (string is required), using default medium 'water'"
            logger.warning(error_msg)
            medium_value = 'water'
        try:
            self.medium = Medium(medium_value)
        except ValueError:
            error_msg = f"Invalid medium in the configuration: '{medium_value}'"
            logger.error(error_msg)
            raise ValueError(error_msg) from None


        volume = self.get_component_static_data(
            component_id="volume",
            unit=DataUnits("MTQ")
        )
        if not isinstance(volume, (float, int, str)):
            error_msg = "No volume of the thermal storage specified in the configuration \
                or invalid type (int or float are possible)."
            logger.error(error_msg)
            raise KeyError(error_msg) from None

        self.volume = float(volume)

        sensor_config = self.get_component_static_data(
            component_id="sensor_config"
        )

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

        try:
            self.calculation_method = ThermalStorageCalculationMethods(
                self.component_config.config.get("calculation_method"))

        except (ValueError, KeyError):
            logger.error("Invalid calculation method in the configuration. "
                         "Using default calculation method "
                         f"{ThermalStorageCalculationMethods.STATIC_LIMITS.value}")
            # default is set in init

    def _prepare_i_o_config(self
                            ):
        """
        Function to prepare the inputs and outputs of the service.
        This function is called before the service is started.
        """
        config = self.component_config
        try:
            input_config = InputModel.model_validate(
                config.inputs.root if isinstance(config.inputs, IOModell)
                else config.inputs)
        except ValidationError:
            error_msg = "Invalid input configuration for the thermal storage"
            logger.error(error_msg)
            raise

        try:
            output_config = OutputModel.model_validate(
                config.outputs.root if isinstance(config.outputs, IOModell)
                else config.outputs)
        except ValidationError:
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
            ValidationError: If the input configuration does not match the sensor configuration
        """

        if self.sensor_config is None:
            raise KeyError("No sensor configuration found in the thermal storage configuration.")
        if self.io_model is None:
            raise KeyError("No I/O model found in the thermal storage configuration.")

        # Check if there are all inputs avaiable
        if self.calculation_method is ThermalStorageCalculationMethods.CONNECTION_LIMITS:
            self.io_model.input.check_load_connection_sensors() # pylint: disable=no-member

        # Check if all inputs are configured in the sensor configuration
        if (self.io_model.input.get_number_storage_sensors() # pylint: disable=no-member
            != len(self.sensor_config.storage_sensors)):
            raise ComponentValidationError(
                "Input configuration does not match sensor configuration."
                "Number of storage temperature sensors in config "
                f"({len(self.sensor_config.storage_sensors)}) "
                "is not the same like the number of inputs "
                f"({self.io_model.input.get_number_storage_sensors()})") # pylint: disable=no-member


    def prepare_start_thermal_storage(
        self,
        static_data: Optional[list[StaticDataEntityModel]] = None,
        ):
        """
        Function to prepare the start of the service, \
            including the loading configuration of the service \
                and preparing the thermal storage.
        It is possible to pass static data for the thermal storage, \
            which will be used to set the static data of the thermal storage. \
                (For a update of the static data)
        Args:
            static_data (Optional[list[StaticDataEntityModel]]): Static data for the thermal storage
        """

        if static_data is not None:

            self.set_component_static_data(
                static_data=static_data,
                static_config=self.component_config.staticdata
            )


        self._prepare_thermal_storage()

        if self.sensor_config is None:
            logger.error("No sensor configuration found in the thermal storage configuration. "
                         "Could not prepare the thermal storage. "
                         "Please check the configuration.")
            return

        self._prepare_i_o_config()

        self._check_input_configuration()

        self.sensor_volumes = self._calculate_volume_per_sensor()

    def run(self):
        """
        Run the thermal storage component.
        """
