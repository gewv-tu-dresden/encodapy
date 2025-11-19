"""
Description: This module contains the definition of a small example service \
    in the form of a heat controller based on a two point controller with hysteresis.
Author: Martin Altenburger, Maximilian Beyer
"""

# pylintrc: There are different examples that may be similar, but this is OK.
# pylint: disable=duplicate-code

from datetime import datetime, timezone

from loguru import logger
from pandas import DataFrame

from encodapy.components.basic_component_config import (
    ControllerComponentModel,
    IOAllocationModel,
)
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataEntityModel,
    InputDataModel,
)
from encodapy.utils.units import DataUnits

from encodapy.utils.datapoints import DataPointGeneral


class MQTTController(ControllerBasicService):
    """
    Class for a small example service
    Service is used to show the basic structure of a service using MQTT
        - read the configuration
        - prepare the start of the service
        - start the service
        - receive the data
        - do the calculation
        - send the data to the output
    """

    def __init__(self) -> None:
        """
        Constructor of the class
        """
        self.heater_config = ControllerComponentModel
        super().__init__()

    def prepare_start(self):
        """
        Function prepare the start of the service, \
            including the loading configuration and the component of the service

        """
        logger.debug("Loading configuration of the service")

        for component in self.config.controller_components:
            if component.type == "MQTTController":
                self.heater_config = component

    def get_component_input(
        self,
        input_entities: list[InputDataEntityModel],
        input_config: IOAllocationModel,
    ) -> tuple[
        (str | float | int | bool | dict | list | DataFrame | None), (DataUnits | None)
    ]:
        """
        Function to get the value of the input data for a specific input configuration \
            of a component of the controller (or a individual one).

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (IOAllocationModel): Configuration of the input

        Returns:
            tuple: Value of the input data, unit of the input data
        """
        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return attribute.data, attribute.unit

        raise KeyError(
            f"Input data {input_config.entity} / {input_config.attribute} not found. "
            "Please check the configuration of the Inputs, Outputs and Static Data."
        )

    def check_heater_command(
        self,
        temperature_setpoint: float,
        temperature_measured: float,
        hysteresis: float,
        heater_status_old: int,
    ) -> int:
        """
        Function to check if the heater should be on or off \
            based on a 2 point controller with hysteresis

        Args:
            temperature_setpoint (float): The setpoint temperature
            temperature_measured (float): The measured temperature (actual temperature)
            hysteresis (float): The hysteresis of the controller
            heater_status_old (bool): The old status of the heater

        Returns:
            bool: The new status of the heater
        """
        if temperature_measured < temperature_setpoint - hysteresis:
            return 1

        if temperature_measured > temperature_setpoint:
            return 0

        if (
            heater_status_old
            and temperature_measured > temperature_setpoint - hysteresis
        ):
            return 1

        return 0

    async def calculation(self, data: InputDataModel):
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        inputs = {}
        for input_key, input_config in self.heater_config.inputs.root.items():
            inputs[input_key], _ = self.get_component_input(
                input_entities=data.input_entities, input_config=input_config
            )

        heater_status = self.check_heater_command(
            temperature_setpoint=(
                inputs["temperature_setpoint"]
                if isinstance(inputs["temperature_setpoint"], (int, float))
                else 0.0
            ),
            temperature_measured=(
                inputs["temperature_measured"]
                if isinstance(inputs["temperature_measured"], (int, float))
                else 0.0
            ),
            hysteresis=(
                self.heater_config.config.root["temperature_hysteresis"].value
                if self.heater_config.config
                and isinstance(self.heater_config.config.root["temperature_hysteresis"], DataPointGeneral)
                and "temperature_hysteresis" in self.heater_config.config.root
                else 5
            ),
            heater_status_old=bool(inputs["heater_status_current"]),
        )

        controller_status = "heating" if heater_status == 1 else "idle"

        return DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id=self.heater_config.outputs.root[
                        "heater_status_recommand"
                    ].entity,
                    attribute_id=self.heater_config.outputs.root[
                        "heater_status_recommand"
                    ].attribute,
                    value=heater_status,
                    timestamp=datetime.now(timezone.utc),
                ),
                DataTransferComponentModel(
                    entity_id=self.heater_config.outputs.root[
                        "controller_status"
                    ].entity,
                    attribute_id=self.heater_config.outputs.root[
                        "controller_status"
                    ].attribute,
                    value=controller_status,
                    timestamp=datetime.now(timezone.utc),
                )
            ]
        )

    async def calibration(self, data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
