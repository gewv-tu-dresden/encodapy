"""
Description: This module contains the definition of a service to calculate \
    the energy in a thermal storage based on the temperature sensors.
Author: Martin Altenburger
"""

from loguru import logger
from encodapy.components.thermal_storage import ThermalStorage
from encodapy.service import ControllerBasicService
from encodapy.utils.models import InputDataModel, DataTransferModel


class ThermalStorageService(ControllerBasicService):
    """
    Class for a thermal storage calculation service

    """

    def __init__(self) -> None:
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
            static_data=self.staticdata,
        )

    async def calculation(self, data: InputDataModel) -> DataTransferModel:
        """
        Function to do the calculation

        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        component_results = self.thermal_storage.run(data)

        return DataTransferModel(components=component_results)

    async def calibration(self, data: InputDataModel) -> None:
        """
        Function to do the calibration of the thermal storage service. 
        This function prepares the thermal storage component with the static data, \
            if this is reloaded.
        It is possible to update the static data of the thermal storage component with \
            rerunning the `prepare_start_thermal_storage` method with new static data.

        Args:
            data (InputDataModel): InputDataModel for the thermal storage component
        """
        if self.env.reload_staticdata:
            logger.debug("Reloading static data for thermal storage")
            self.thermal_storage.calibrate(static_data=data.static_entities)
