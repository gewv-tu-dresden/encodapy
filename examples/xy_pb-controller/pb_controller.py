"""
Description: This module contains the definition of a example service \
    connected with TRNSYS-TUD to manage a system plant in simulation.
Author: Maximilian Beyer
"""

from datetime import datetime
from typing import Optional, Union

from loguru import logger

from encodapy.config.models import ControllerComponentModel, OutputModel
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataEntityModel,
    InputDataModel,
)


class PBController(ControllerBasicService):
    """
    Class for a example service controller for Prototyping and Testing
    Service is used to control a pellet boiler
        - read the configuration
        - prepare the start of the service
        - start the service
        - receive the data
        - do the controlling calculation
        - send the data to the output
    """

    def __init__(self, *args, **kwargs):
        self.controller_config: Optional[ControllerComponentModel] = None
        self.data: Optional[InputDataModel] = None
        super().__init__(*args, **kwargs)

    def prepare_start(self) -> None:
        """
        prepare the start of the trnsys controller service

        """
        logger.info("Prepare Start of Service")

        # add own functionality for the current service here
        # get the controller configuration
        self.controller_config = self.get_controller_config(type_name="pb-controller")

        logger.info("PelletBoiler Controller Service prepared successfully")

    def get_controller_config(self, type_name: str) -> ControllerComponentModel:
        """
        Function to get the configuration of the system controller

        Returns:
            dict: The configuration of the system controller
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for component in self.config.controller_components:
            if component.type == type_name:
                logger.debug(
                    f"Found heat controller configuration for type '{type_name}'"
                )
                return component
        raise ValueError("No heat controller configuration found")

    def get_output_config(self, output_entity: str) -> OutputModel:
        """
        Function to get the output configuration of a specific entity

        Args:
            output_entity (str): The ID of the output entity

        Returns:
            OutputModel: The output configuration
        """
        if self.config is None:
            raise ValueError("No configuration found")

        for entity in self.config.outputs:
            if entity.id == output_entity:
                logger.debug(f"Found output configuration for entity '{output_entity}'")
                return entity
        raise ValueError(
            f"No output configuration for the entity '{output_entity}' found"
        )

    def get_input_entity(
        self, data: InputDataModel, entity_id: str
    ) -> InputDataEntityModel:
        """
        Function to get the input entity from the data

        Args:
            data (InputDataModel): The input data model

        Returns:
            InputDataEntityModel | None: The input entity or None if not found
        """
        if data.input_entities:
            for entity in data.input_entities:
                if entity.id == entity_id:
                    return entity
        raise ValueError(f"Input entity with ID '{entity_id}' not found in data")

    def get_inputs(self, input_entity: InputDataEntityModel) -> dict:
        """
        Function to get the inputs and their values from the entity

        Args:
            input_entity (InputDataEntityModel): The input entity model

        Returns:
            inputs (dict): Dictionary in the Format {attribute_id: value}
        """
        inputs = {}
        for attribute in input_entity.attributes:
            # check if data type is float, int, str or bool
            if isinstance(attribute.data, (float, int, str, bool)):
                data = attribute.data

            else:
                logger.warning(
                    f"Input entity {input_entity.id} with attribute "
                    f"{attribute.id} has unsupported data type: "
                    f"{type(attribute.data)}"
                )
                data = None

            # add the input data to the inputs dictionary
            inputs[attribute.id] = data

        return inputs

    async def calculation(self, data: InputDataModel) -> Union[DataTransferModel, None]:
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """
        # check if the controller configuration is available
        if self.controller_config is None:
            raise ValueError("Prepare the start of the service before calculation")

        # get the current input entities from the data
        boiler_input_entity = self.get_input_entity(data=data, entity_id="PB-Outputs")

        inputs = self.get_inputs(boiler_input_entity)

        t_dhw_measured = inputs["WarmwasserTempAktu"] / 10

        if t_dhw_measured < 60:
            power_on_pk = 1
        else:
            power_on_pk = 0

        power_on_pk_payload = {
            "DATAPOINT": "ZundungEin",
            "SENSOR": "TEMPERATUR",
            "VALUE": str(power_on_pk),
            "UNIT": "",
            "TIME": datetime.now(),
        }

        # create the output data
        components = []

        components.append(
            DataTransferComponentModel(
                entity_id="PB-Inputs",
                attribute_id="ZundungEin",
                value=str(power_on_pk_payload),
                timestamp=datetime.now(),
            )
        )

        return DataTransferModel(components=components)

    async def calibration(self, data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
