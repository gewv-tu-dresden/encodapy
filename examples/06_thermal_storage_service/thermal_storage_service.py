"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""
from datetime import datetime, timezone
from loguru import logger
from encodapy.components.thermal_storage import ThermalStorage
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    InputDataModel,
    DataTransferModel,
    DataTransferComponentModel
    )

class ThermalStorageService(ControllerBasicService):
    """
    Class for a thermal storage calculation service

    """

    def __init__(self)-> None:
        """
        Constructor for the ThermalStorageService
        """
        self.thermal_storage: ThermalStorage
        super().__init__()

    def prepare_start(self):
        """ Function to prepare the thermal storage service for start
        This function loads the thermal storage configuration \
            and initializes the thermal storage component.
        """

        self.thermal_storage = ThermalStorage(
            config=self.config.controller_components,
            component_id="thermal_storage",
            static_data=self.staticdata
            )


    async def calculation(self,
                          data: InputDataModel
                          )-> DataTransferModel:
        """
        Function to do the calculation

        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """
        if self.thermal_storage.io_model is None:
            logger.warning("Thermal storage IO model is not set.")
            return DataTransferModel(components=[])

        self.thermal_storage.set_temperature_values(input_entities=data.input_entities)

        storage__energy = self.thermal_storage.get_storage_energy_current()
        storage__level = self.thermal_storage.calculate_state_of_charge()
        logger.debug("Energy Storage Level: " + str(storage__level) + " %")
        logger.debug("Energy of the Storage: " + str(storage__energy) + " Wh")

        components = []


        # pylint problems see: https://github.com/pylint-dev/pylint/issues/4899
        if self.thermal_storage.io_model.output.storage__level is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.thermal_storage.io_model.output.storage__level.entity,  # pylint: disable=no-member
                attribute_id=self.thermal_storage.io_model.output.storage__level.attribute,  # pylint: disable=no-member
                value=storage__level,
                timestamp=datetime.now(timezone.utc)
            ))

        if self.thermal_storage.io_model.output.storage__energy is not None:  # pylint: disable=no-member
            components.append(DataTransferComponentModel(
                entity_id=self.thermal_storage.io_model.output.storage__energy.entity,  # pylint: disable=no-member
                attribute_id=self.thermal_storage.io_model.output.storage__energy.attribute,  # pylint: disable=no-member
                value=storage__energy,
                timestamp=datetime.now(timezone.utc)
            ))

        return DataTransferModel(components=components)


    async def calibration(self,
                          data: InputDataModel
                          )-> None:
        """
        Function to do the calibration of the thermal storage service. 
        This function prepares the thermal storage component with the static data, \
            if this is reloaded.
        It is possible to update the static data of the thermal storage component with \
            rerunning the `prepare_start_thermal_storage` method with new static data.

        Args:
            data (InputDataModel): InputDataModel for the thermal storage component
        """
        if self.reload_staticdata:
            logger.debug("Reloading static data for thermal storage")
            self.thermal_storage.prepare_start_thermal_storage(static_data=data.static_entities)
