"""
Description: This module contains the definition of a small example service \
    in the form of a heat controller based on a two point controller with hysteresis.
Author: Martin Altenburger
"""
from typing import Union
from datetime import datetime, timezone
from loguru import logger
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    InputDataModel,
    InputDataEntityModel,
    DataTransferModel,
    DataTransferComponentModel
    )


class ExampleService(ControllerBasicService):
    """
        Class for a small example service
        Service is used to show the basic structure of a service
            - read the configuration
            - prepare the start of the service
            - start the service
            - reseive the data
            - do the calculation
            - send the data to the output
    """
    def __init__(self):
        """
        Constructor of the class
        """
        self.heater_config = None
        super().__init__()


    def prepare_start(self):
        """
        Function prepare the start of the service, \
            including the loading configuration of the service

        """
        logger.debug("Loading configuration of the service")

        self.heater_config = self.get_heat_controller_config()

    def get_heat_controller_config(self)-> dict:
        """
        Function to get the configuration of the heat controller

        Returns:
            dict: The configuration of the heat controller
        """
        for component in self.config.controller_components:
            if component.type == "heat_controller":
                return component
        raise ValueError("No heat controller configuration found")

    def check_heater_command(self,
                             temperature_setpoint:float,
                             temperature_measured:float,
                             hysteresis:float,
                             heater_status_old:bool
                             )-> bool:
        """
        Function to check if the heater should be on or off \
            based on a 2 point controller with hysteresis

        Args:
            temperature_setpoint (float): The setpoint temperature
            temperature_measured (float): The measured temperature (acutal temperature)
            hysteresis (float): The hysteresis of the controller
            heater_status_old (bool): The old status of the heater

        Returns:
            bool: The new status of the heater
        """
        if temperature_measured < temperature_setpoint - hysteresis:
            return True

        if temperature_measured > temperature_setpoint:
            return False

        if heater_status_old and temperature_measured > temperature_setpoint - hysteresis:
            return True

        return False

    def get_input_values(self,
                         input_entities:list[InputDataEntityModel],
                         input_config:dict,
                         )-> Union[float, int, str, bool]:
        """
        Function to get the values of the input data

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (dict): Configuration of the input

        Returns:
            Union[float, int, str, bool]: The value of the input data
        """
        for input_data in input_entities:
            if input_data.id == input_config["entity"]:
                for attribute in input_data.attributes:
                    if attribute.id == input_config["attribute"]:
                        return attribute.data
        raise ValueError(f"Input data {input_config['entity']} not found")

    async def calculation(self,
                          data: InputDataModel
                          ):
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        inputs = {}
        for input_key, input_config in self.heater_config.inputs.items():
            inputs[input_key] = self.get_input_values(input_entities=data.input_entities,
                                                      input_config=input_config)

        heater_status = self.check_heater_command(
            temperature_setpoint=inputs["temperature_setpoint"],
            temperature_measured=inputs["temperature_measured"],
            hysteresis=self.heater_config.config["temperature_hysteresis"],
            heater_status_old=bool(inputs["heater_status"]))

        return DataTransferModel(components=[
            DataTransferComponentModel(
                entity_id=self.heater_config.outputs["heater_status"]["entity"],
                attribute_id=self.heater_config.outputs["heater_status"]["attribute"],
                value=heater_status,
                timestamp=datetime.now(timezone.utc))
                    ]
                )
    async def calibration(self,
                          data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
