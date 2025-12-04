"""
Simple Method to caluculate the energy in a the thermal storage
Author: Martin Altenburger, Paul Seidel
"""
from typing import Optional, Union
import math
from datetime import datetime
from loguru import logger
import pandas as pd
from encodapy.components.basic_component import BasicComponent
from encodapy.components.basic_component_config import (
    ComponentValidationError,
    ControllerComponentModel,
)
from encodapy.utils.datapoints import DataPointNumber
from encodapy.components.thermal_storage.thermal_storage_config import (
    TemperatureLimits,
    ThermalStorageCalculationMethods,
    ThermalStorageConfigData,
    ThermalStorageEnergyTypes,
    ThermalStorageInputData,
    ThermalStorageOutputData,
    TemperatureExtrema
)
#TODO remove
# from encodapy.components.thermal_storage.calibration_file import (
#     save_calibration_json
# )
from encodapy.components.thermal_storage.calibration_data import (
    CalibrationData
)
from encodapy.utils.mediums import get_medium_parameter
from encodapy.utils.models import (
    InputDataModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import DataUnits

class ThermalStorage(BasicComponent):
    """
    Class to calculate the energy in a thermal storage.

    Service needs to be prepared before use (`prepare_start_thermal_storage`).

    Args:
        config (Union[ControllerComponentModel, list[ControllerComponentModel]]): \
            Configuration of the thermal storage
        static_data (Optional[list[StaticDataEntityModel]], optional): \
            Static data of the ThermalStorage
        component_id (str): ID of the thermal storage component
    
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Basic initialization of the thermal storage
        # Configuration of the thermal storage

        # Variables for the calculation
        self.sensor_volumes: Optional[dict] = None
        self.config_data: ThermalStorageConfigData
        self.input_data: ThermalStorageInputData
        self.output_data: ThermalStorageOutputData

        self.sensor_values_stored: dict[int, pd.Series] = {}
        # TODO: maybe use other structure from collections import deque or np.array --> less ram

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )
        # Set the default value for the reference state of charge to None - start of the service
        self.config_data.load_level_check.ref_state_of_charge = None
        self.calibration_data = CalibrationData(db_path=self.config_data.calibration.db_path)

    def _calculate_volume_per_sensor(self) -> dict:
        """
        Function to calculate the volume per sensor in the thermal storage

        Returns:
            dict: Volume per sensor in the thermal storage in m³
        """

        sensor_volumes = {}

        sensor_height_ref = 0.0

        for index, storage_sensor in enumerate(
            self.config_data.sensor_config.value.storage_sensors
        ):
            if index == len(self.config_data.sensor_config.value.storage_sensors) - 1:
                sensor_height_new = 100.0
            else:
                sensor_height_new = (
                    storage_sensor.height
                    + self.config_data.sensor_config.value.storage_sensors[
                        index + 1
                    ].height
                ) / 2

            sensor_volumes[index] = (
                (sensor_height_new - sensor_height_ref)
                / 100
                * self.config_data.volume.value
            )
            sensor_height_ref = sensor_height_new

        return sensor_volumes

    def _get_sensor_volume(self, sensor: int) -> float:
        """
        Function to get the volume of the sensors in the thermal storage

        Returns:
            float: Volume of the sensors in the thermal storage in m³
        """
        if self.sensor_volumes is None:
            raise ValueError("Sensor volumes are not set.")
        if sensor not in self.sensor_volumes:
            raise ValueError(f"Sensor {sensor} is not configured.")

        return round(self.sensor_volumes[sensor], 3)

    def _get_connection_limits(
        self, sensor_id: int, config_limits: TemperatureLimits
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

        if self.input_data.load_temperature_out is None:
            logger.warning("Load temperature outflow is not set.")
            return config_limits
        if self.input_data.load_temperature_in is None:
            logger.warning("Load temperature inflow is not set.")
            return config_limits

        if sensor_id == 0:
            return TemperatureLimits(
                minimal_temperature=self.input_data.load_temperature_out.value,
                maximal_temperature=config_limits.maximal_temperature,
                reference_temperature=config_limits.reference_temperature,
            )

        return TemperatureLimits(
            minimal_temperature=self.input_data.load_temperature_in.value,
            maximal_temperature=config_limits.maximal_temperature,
            reference_temperature=config_limits.reference_temperature,
        )

    def _get_sensor_limits(self, sensor_id: int) -> TemperatureLimits:
        """
        Function to get the temperature limits of the sensors in the thermal storage
        Args:
            sensor (int): ID of the sensor in the thermal storage (0=top, 1=second, ...)
        Returns:
            TemperatureLimits: Temperature limits of the sensors in the thermal storage
        """

        config_limits = self.config_data.sensor_config.value.storage_sensors[
            sensor_id
        ].limits

        if (
            self.config_data.calculation_method.value
            == ThermalStorageCalculationMethods.STATIC_LIMITS
        ):
            return config_limits

        if (
            self.config_data.calculation_method.value
            == ThermalStorageCalculationMethods.CONNECTION_LIMITS
        ):
            limits = self._get_connection_limits(
                sensor_id=sensor_id, config_limits=config_limits
            )

            return limits

        if (
            self.config_data.calculation_method.value
            == ThermalStorageCalculationMethods.HISTORICAL_LIMITS
        ):
            #TODO Add flexible limits method
            return config_limits

        logger.warning(
            f"Unknown calculation method: {self.config_data.calculation_method.value}"
        )

        return config_limits

    def get_storage_temperature_sensor_value(self,
                                             sensor_index:int) -> DataPointNumber:
        """
        Function to get the temperature value of a sensor in the thermal storage
        Args:
            sensor_index (int): ID of the sensor in the thermal storage (0=top, 1=second, ...)
        
        Returns:
            DataPointNumber: Temperature value of the sensor in the thermal storage in °C
        """
        temperature_sensor = f"temperature_{sensor_index+1}"
        try:
            temperature: DataPointNumber = getattr(
                self.input_data, temperature_sensor
            )
        except AttributeError as e:
            error_msg = (
                f"Temperature sensor '{temperature_sensor}' "
                "not found in input data."
            )
            logger.error(error_msg)
            raise AttributeError(error_msg) from e
        if not isinstance(temperature, DataPointNumber):
            error_msg = (
                f"Temperature sensor '{temperature_sensor}' "
                "is not of type DataPointNumber."
            )
            logger.error(error_msg)
            raise TypeError(error_msg)
        if temperature is None or temperature.value is None:
            error_msg = (
                f"Temperature value for sensor '{temperature_sensor}' is not set."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        return temperature

    def get_storage_energy_content(
        self, energy_type: ThermalStorageEnergyTypes
    ) -> float:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            float: Nominal energy content of the thermal storage in Wh
        """
        # Check if the calculation is possible

        if self.sensor_volumes is None:
            raise ValueError("Sensor volumes are not set.")

        nominal_energy = 0

        for index, _ in enumerate(self.config_data.sensor_config.value.storage_sensors):
            temperature = self.get_storage_temperature_sensor_value(sensor_index=index)

            medium_parameter = get_medium_parameter(
                medium=self.config_data.medium.value,
                temperature=temperature.value,
            )

            sensor_limits = self._get_sensor_limits(sensor_id=index)

            if energy_type is ThermalStorageEnergyTypes.NOMINAL:
                temperature_difference = (
                    sensor_limits.maximal_temperature
                    - sensor_limits.minimal_temperature
                )

            elif energy_type is ThermalStorageEnergyTypes.MINIMAL:
                temperature_difference = (
                    sensor_limits.minimal_temperature
                    - sensor_limits.reference_temperature
                )

            elif energy_type is ThermalStorageEnergyTypes.MAXIMAL:
                temperature_difference = (
                    sensor_limits.maximal_temperature
                    - sensor_limits.reference_temperature
                )

            elif energy_type is ThermalStorageEnergyTypes.CURRENT:
                temperature_difference = (
                    temperature.value - sensor_limits.minimal_temperature
                )

            else:
                raise ValueError(f"Unknown energy type: {energy_type}")

            nominal_energy += (
                temperature_difference
                * self.sensor_volumes[index]
                * medium_parameter.rho
                * medium_parameter.cp
                / 3.6
            )

        return round(nominal_energy, 2)

    def get_storage_energy_nominal(self) -> tuple[float, DataUnits]:
        """
        Function to calculate the nominal energy content of the thermal storage

        Returns:
            tuple[float, DataUnits]: Nominal energy content of the thermal storage in Wh
        """

        return (
            self.get_storage_energy_content(ThermalStorageEnergyTypes.NOMINAL),
            DataUnits.WHR,
        )

    def get_storage_energy_minimum(self) -> tuple[float, DataUnits]:
        """
        Function to get the minimum energy content of the thermal storage

        Returns:
            tuple[float, DataUnits]: Minimum energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return (
            self.get_storage_energy_content(ThermalStorageEnergyTypes.MINIMAL),
            DataUnits.WHR,
        )

    def get_storage_energy_maximum(self) -> tuple[float, DataUnits]:
        """
        Function to get the maximum energy content of the thermal storage

        Returns:
            tuple[float, DataUnits]: Maximum energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return (
            self.get_storage_energy_content(ThermalStorageEnergyTypes.MAXIMAL),
            DataUnits.WHR,
        )

    def get_storage_energy_current(self) -> tuple[float, DataUnits]:
        """
        Function to get the current energy content of the thermal storage

        Returns:
            tuple[float, DataUnits]: Current energy content of the thermal storage in Wh
        Raises:
            ValueError: If the thermal storage is not usable or the sensor values are not set
        """
        return (
            self.get_storage_energy_content(ThermalStorageEnergyTypes.CURRENT),
            DataUnits.WHR,
        )

    def get_storage_loading_potential_nominal(self) -> tuple[float, DataUnits]:
        """
        Function to get the loading potential of the thermal storage, \
            which is the difference between the nominal and current energy content.

        Returns:
            tuple[float, DataUnits]: Loading potential of the thermal storage in Wh
        """
        nominal_energy = self.get_storage_energy_nominal()[0]
        current_energy = self.get_storage_energy_current()[0]
        loading_potential = round(nominal_energy - current_energy, 2)
        return loading_potential, DataUnits.WHR

    def set_input_data(self, input_data: InputDataModel) -> None:
        """
        Function to set the sensor values in the thermal storage

        Args:
            input_entities (list[InputDataEntityModel]): Input entities with temperature values
        Raises:
            ValueError: If the thermal storage is not usable or \
                the sensor values are not set correctly
        """
        super().set_input_data(input_data=input_data)
        if (
            self.config_data.calculation_method.value
            is ThermalStorageCalculationMethods.CONNECTION_LIMITS
        ):
            self.input_data.check_load_connection_sensors()

    def _check_temperatur_of_highest_sensor(self, state_of_charge: float) -> float:
        """
        Function to check if the temperature of the highest sensor is too low, \
            so there is no energy left
        Args:
            state_of_charge (float): Current state of charge

        Returns:
            float: Adjusted state of charge
        """
        if self.config_data.load_level_check.enabled is False:
            return state_of_charge

        temperature_limits = self._get_sensor_limits(sensor_id=0)
        ref_temperature = (
            temperature_limits.minimal_temperature
            + (
                temperature_limits.maximal_temperature
                - temperature_limits.minimal_temperature
            )
            * (self.config_data.load_level_check.minimal_level / 100)
        )

        if self.input_data.temperature_1.value >= ref_temperature:
            self.config_data.load_level_check.ref_state_of_charge = None
            return state_of_charge
        if self.input_data.temperature_1.value < temperature_limits.minimal_temperature:
            return 0
        if self.config_data.load_level_check.ref_state_of_charge is None:
            self.config_data.load_level_check.ref_state_of_charge = state_of_charge

        denominator =  ref_temperature - temperature_limits.minimal_temperature

        if math.isclose(denominator, 0, abs_tol=1e-9):
            logger.debug("Denominator in state of charge adjustment is too small, "
                         "could not check the thermal storage level.")
            current_factor = 1.0
        else:
            current_factor = (
                self.input_data.temperature_1.value
                - temperature_limits.minimal_temperature
            ) / denominator
        return (
            current_factor
            * self.config_data.load_level_check.ref_state_of_charge
            )

    def get_state_of_charge(self) -> tuple[float, DataUnits]:
        """
        Function to calculate the state of charge of the thermal storage

        If the temperature of the highest sensor is too low, there is no energy left, \
            so the state of charge is 0.

        Returns:
            tuple[float, DataUnits]: State of charge of the thermal storage in percent (0-100)
        """
        state_of_charge = (
            self.get_storage_energy_current()[0]
            / self.get_storage_energy_nominal()[0]
            * 100
        )

        state_of_charge = self._check_temperatur_of_highest_sensor(
            state_of_charge=state_of_charge
        )

        return round(state_of_charge, 2), DataUnits.PERCENT

    def get_storage__mean_temperature_maximal(self) -> DataPointNumber:
        """
        Function to calculate the mean maximal temperature of the thermal storage
        Using the maximal temperature of each sensor and \
        weighting it with the volume of the sensor

        Returns:
            DataPointNumber: Mean maximal temperature of the thermal storage in °C
        """
        max_temperatures: list[float] = []
        storage_volume = self.config_data.volume.value
        for index, storage_sensor in enumerate(
            self.config_data.sensor_config.value.storage_sensors
        ):

            sensor_volume = self._get_sensor_volume(sensor=index)

            max_temperatures.append(
                storage_sensor.limits.maximal_temperature * sensor_volume
            )

        return DataPointNumber(
            value=round(sum(max_temperatures) / storage_volume, 2),
            unit=DataUnits.DEGREECELSIUS,
        )

    def _check_input_configuration(self):
        """
        Function to check the input configuration of the service \
            in comparison to the sensor configuration.
        The inputs needs to match the sensor configuration.
        Raises:
            ValidationError: If the input configuration does not match the sensor configuration
        """

        if self.io_model is None:
            raise KeyError("No I/O model found in the thermal storage configuration.")

        inputs = ThermalStorageInputData.model_validate(self.io_model.input)
        # Check if there are all inputs avaiable
        if (
            self.config_data.calculation_method.value
            is ThermalStorageCalculationMethods.CONNECTION_LIMITS
        ):
            inputs.check_load_connection_sensors()

        # Check if all inputs are configured in the sensor configuration
        if inputs.get_number_storage_sensors() != len(
            self.config_data.sensor_config.value.storage_sensors
        ):
            raise ComponentValidationError(
                "Input configuration does not match sensor configuration."
                "Number of storage temperature sensors in config "
                f"({len(self.config_data.sensor_config.value.storage_sensors)}) "
                "is not the same like the number of inputs "
                f"({inputs.get_number_storage_sensors()})"
            )

    def prepare_component(self):
        """
        Function to prepare the thermal storage component for the start of the service
        """

        self._check_input_configuration()

        self.sensor_volumes = self._calculate_volume_per_sensor()

    def calculate(self):
        """
        Function to calculate the thermal storage values
        """
        storage__energy = self.get_storage_energy_current()
        storage__energy_datapoint = DataPointNumber(
            value=storage__energy[0],
            unit=storage__energy[1],
        )

        state_of_charge = self.get_state_of_charge()
        state_of_charge_datapoint = DataPointNumber(
            value=state_of_charge[0],
            unit=state_of_charge[1],
        )

        loading_potential = self.get_storage_loading_potential_nominal()
        loading_potential_datapoint = DataPointNumber(
            value=loading_potential[0],
            unit=loading_potential[1],
        )

        self.output_data = ThermalStorageOutputData(
            storage__energy=storage__energy_datapoint,
            storage__level=state_of_charge_datapoint,
            storage__loading_potential_nominal=loading_potential_datapoint,
        )

        if self.config_data.calculation_method.value \
            == ThermalStorageCalculationMethods.HISTORICAL_LIMITS:
            logger.debug("Storing thermal storage sensor values.")
            self.store_storage_temperature_history()

    def store_storage_temperature_history(self)-> None:
        """
        Function to store the temperature history of the thermal storage

        Stores the temperature values of each sensor in a pandas Series
        in the sensor_values_stored dictionary with the sensor index as key.

        TODO: Maybe use other structure collections.deque or np.array --> less ram
        """
        for index, _ in enumerate(self.config_data.sensor_config.value.storage_sensors):
            try:
                temperature = self.get_storage_temperature_sensor_value(sensor_index=index)
                # Store the temperature value in the history ??
                if not isinstance(temperature.value, (int, float)):
                    raise ValueError("Temperature value is not a number.")
                if temperature.time is None:
                    raise ValueError("Temperature time is not set.")
                if index not in self.sensor_values_stored:
                    self.sensor_values_stored[index] = pd.Series(
                        dtype=float,
                        index=pd.DatetimeIndex([], tz="UTC"))

                self.sensor_values_stored[index].at[pd.to_datetime(temperature.time)] = \
                    float(temperature.value)
            except (AttributeError, ValueError, TypeError) as e:
                logger.warning(f"Could not store temperature for sensor {index}: {e}")
                continue

    def handle_storage_sensor_historical_data(self,
                                               sensor_index:int
                                               ) -> Optional[TemperatureExtrema]:
        """
        Function to handle the historical data of a storage sensor
        Args:
            sensor_index (int): Index of the sensor in the thermal storage
        Returns:
            Optional[TemperatureExtrema]: Historical data of the sensor
        """

        historical_data = self.sensor_values_stored.get(sensor_index, None)

        new_extrema: Optional[TemperatureExtrema] = None
        timerange: Optional[pd.Timedelta] = None

        if historical_data is None:
            logger.debug(f"No historical data found for sensor {sensor_index}.")
        else:
            timerange = historical_data.index.max() - historical_data.index.min()

        if historical_data is not None and timerange is not None \
            and timerange >= pd.Timedelta(
            hours=self.config_data.calibration.historical_timerange_minimum
        ):
            new_extrema = TemperatureExtrema(
                minimal_temperature=min(historical_data),
                maximal_temperature=max(historical_data),
                time=datetime.utcnow()
            )

        old_extrema: Optional[TemperatureExtrema] = None
        if self.calibration_data.db_path is not None:
            old_extrema = self.calibration_data.load_extrema_sqlite(sensor_index=sensor_index)

        if old_extrema is not None and new_extrema is not None:
            temperature_extrema = TemperatureExtrema(
                minimal_temperature=min(
                    new_extrema.minimal_temperature,
                    old_extrema.minimal_temperature
                ),
                maximal_temperature=max(
                    new_extrema.maximal_temperature,
                    old_extrema.maximal_temperature
                ),
                time=datetime.utcnow()
            )
        elif new_extrema is not None:
            temperature_extrema = new_extrema
        elif old_extrema is not None:
            temperature_extrema = old_extrema
        else:
            logger.warning(
                f"Could not determine extrema for sensor {sensor_index}."
            )
            return None

        #TODO remove
        # if self.config_data.calibration.storage_path is not None:
        #     save_calibration_json(
        #         path=self.config_data.calibration.storage_path,
        #         data=temperature_extrema.model_dump(),
        #     )

        if self.calibration_data.db_path is not None:
            self.calibration_data.save_extrema_sqlite(
                sensor_index=sensor_index,
                extrema=temperature_extrema
            )
        # Remove old data from the historical data / Retention policy
        if sensor_index in self.sensor_values_stored \
            and self.sensor_values_stored[sensor_index] is not None:
            cutoff = self.sensor_values_stored[sensor_index].index.max() - pd.Timedelta(
                hours=self.config_data.calibration.historical_timerange_retention)
            self.sensor_values_stored[sensor_index] = \
                self.sensor_values_stored[sensor_index].truncate(before=cutoff)

        return temperature_extrema

    def calibrate_historical_based_sensor_configuration(self)-> None:
        """
        Function to calibrate the thermal storage component based on historical data
        
        Uses historical temperature data to adjust the sensor configuration limits
        TODO: Do we need a limit for the adjustment - the upper and lower limit for some reason?
        """
        if self.calibration_data.db_path is not None:
            self.config_data.sensor_config.value = (
                self.calibration_data.load_limits_sqlite(
                    sensor_config=self.config_data.sensor_config.value
                ))
        for index, _ in enumerate(self.config_data.sensor_config.value.storage_sensors):

            sensor_config = self.config_data.sensor_config.value.storage_sensors[index]

            historical_data = self.handle_storage_sensor_historical_data(sensor_index=index)


            if historical_data is None:
                logger.warning(
                    f"Could not calibrate sensor {index} due to missing historical data.")
                continue
            # Calculate new limits based on historical data and configuration
            # / do not adjust protected sensors
            if index in self.config_data.calibration.protected_sensors_lower_limit \
                or sensor_config.name in self.config_data.calibration.protected_sensors_lower_limit:
                minimal_temperature = sensor_config.limits.minimal_temperature
            else:
                minimal_temperature = round((
                    historical_data.minimal_temperature
                    * (1-self.config_data.calibration.historical_data_margin/100)
                    + sensor_config.limits.minimal_temperature
                    ) / 2,1)
            if index in self.config_data.calibration.protected_sensors_upper_limit \
                or sensor_config.name in self.config_data.calibration.protected_sensors_upper_limit:
                maximal_temperature = sensor_config.limits.maximal_temperature
            else:
                maximal_temperature = round((
                    historical_data.maximal_temperature
                    * (1+self.config_data.calibration.historical_data_margin/100)
                    + sensor_config.limits.maximal_temperature
                    ) / 2,1)

            try:
                # Calibrate the sensor configuration based on historical data
                # For example, adjust the limits based on historical temperature data
                sensor_config.limits = TemperatureLimits(
                    minimal_temperature=minimal_temperature,
                    maximal_temperature=maximal_temperature,
                    reference_temperature=sensor_config.limits.reference_temperature,
                )

                self.config_data.sensor_config.value.storage_sensors[index] = sensor_config

            except ValueError as e:
                logger.error(f"Error during calibration of sensor {index}: {e}")
                continue

        if self.calibration_data.db_path is not None:
            self.calibration_data.save_limits_sqlite(
                sensor_config=self.config_data.sensor_config.value
            )
        #TODO change logger to debug
        logger.info(
            "Calibrated sensor configuration: "
            f"{self.config_data.sensor_config.value.storage_sensors}"
            )

    def calibrate(self,
                  static_data: Optional[list[StaticDataEntityModel]] = None
                  )-> None:
        """
        Function to calibrate the thermal storage component
        """
        print(self.sensor_values_stored)
        if self.config_data.calculation_method.value \
            == ThermalStorageCalculationMethods.HISTORICAL_LIMITS:

            logger.debug("Calibrating thermal storage based on historical data.")

            self.calibrate_historical_based_sensor_configuration()
