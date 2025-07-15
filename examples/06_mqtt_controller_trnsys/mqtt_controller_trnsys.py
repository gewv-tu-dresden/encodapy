"""
Description: This module contains the definition of a example service \
    connected with TRNSYS-TUD to manage a system plant in simulation.
Author: Maximilian Beyer
"""

from datetime import datetime, timezone
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


class MQTTControllerTrnsys(ControllerBasicService):
    """
    Class for a example service controller for Trnsys
    Service is used to control a hybrid plant with heat pump and pellet boiler
        - read the configuration
        - prepare the start of the service
        - start the service
        - receive the data
        - do the controlling calculation
        - send the data to the output
    """

    def __init__(self, *args, **kwargs):
        self.controller_config: Optional[ControllerComponentModel] = None
        self.controller_outputs_for_trnsys: Optional[OutputModel] = None
        self.data: Optional[InputDataModel] = None
        self.timestamp_last_output: datetime = datetime.now()
        super().__init__(*args, **kwargs)

    def prepare_start(self) -> None:
        """
        prepare the start of the trnsys controller service

        """
        logger.info("Prepare Start of Service")

        # add own functionality for the current service here
        # get the controller configuration
        self.controller_config = self.get_controller_config(
            type_name="system-controller"
        )
        # get the output configuration for TRNSYS (needed for the full message "SAMMELN")
        self.controller_outputs_for_trnsys = self.get_output_config(
            output_entity="TRNSYS-Inputs"
        )

        logger.info("TRNSYS Controller Service prepared successfully")

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

    # def get_input_values(
    #     self,
    #     input_entities: list[InputDataEntityModel],
    #     input_config: dict,
    # ) -> Union[float, int, str, bool, None]:
    #     """
    #     Function to get the values of the input data

    #     Args:
    #         input_entities (list[InputDataEntityModel]): Data of input entities
    #         input_config (dict): Configuration of the input

    #     Returns:
    #         Union[float, int, str, bool]: The value of the input data
    #     """
    #     for input_data in input_entities:
    #         if input_data.id == input_config["entity"]:
    #             for attribute in input_data.attributes:
    #                 if attribute.id == input_config["attribute"]:
    #                     # check if data type is float, int, str or bool
    #                     if isinstance(attribute.data, (float, int, str, bool)):
    #                         return attribute.data

    #                     logger.warning(
    #                         f"Input data {input_config['entity']} with attribute "
    #                         f"{input_config['attribute']} has unsupported data type: "
    #                         f"{type(attribute.data)}"
    #                     )
    #                     return None
    #     raise ValueError(f"Input data {input_config['entity']} not found")

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
            temperature_measured (float): The measured temperature (acutal temperature)
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

    def get_inputs(self, input_entity: InputDataEntityModel) -> dict:
        """
        Function to get the inputs and their values from the entity

        Returns:
            inputs (dict): Dictionary with the input values
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

    def newer_than_timestamp_last_output(
        self, input_entity: InputDataEntityModel
    ) -> bool:
        """
        Check if the inputs in MQTT entity are all newer than timestamp of the latest output.

        """
        for attribute in input_entity.attributes:
            if attribute.latest_timestamp_input is None:
                return False
            if attribute.latest_timestamp_input < self.timestamp_last_output:
                return False
        return True

    async def calculation(self, data: InputDataModel) -> Union[DataTransferModel, None]:
        """
        Function to do the calculation
        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """
        # check if the controller configuration is available
        if self.controller_config is None or self.controller_outputs_for_trnsys is None:
            raise ValueError("Prepare the start of the service before calculation")

        # get the current input entities from the data
        trnsys_input_entity = self.get_input_entity(
            data=data, entity_id="TRNSYS-Outputs"
        )

        boiler_input_entity = self.get_input_entity(
            data=data, entity_id="Boiler-Outputs"
        )

        # get last timestamp of the inputs
        trnsys_updated = self.newer_than_timestamp_last_output(
            input_entity=trnsys_input_entity
        )
        boiler_updated = self.newer_than_timestamp_last_output(
            input_entity=boiler_input_entity
        )

        # if trnsys_updated is false, continue to wait for new inputs
        if not trnsys_updated:
            return None

        trnsys_inputs = self.get_inputs(input_entity=trnsys_input_entity)
        boiler_inputs = self.get_inputs(input_entity=boiler_input_entity)

        components = []
        sammeln_payload = ""

        for output_key, output_config in self.controller_config.outputs.items():
            if output_key == "full_trnsys_message":
                # skip the full output, it is handled separately
                continue

            entity_id = output_config["entity"]
            attribute_id = output_config["attribute"]

            # TODO MB: Calculate the values based on the inputs here, add them to the DataTransferComponentModel and the sammeln_payload
            
            # add standard message of the outputs to DataTransferComponentModel
            components.append(
                DataTransferComponentModel(
                    entity_id=entity_id,
                    attribute_id=attribute_id,
                    value=None,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            # build the trnsys payload for the full message
            for output_attribute in self.controller_outputs_for_trnsys.attributes:
                if output_attribute.id == attribute_id:
                    if output_attribute.id == "OP_S_WP":
                        trnsys_value = 1
                    elif output_attribute.id == "OP_S_WP_TWE":
                        trnsys_value = 0
                    elif output_attribute.id == "n_WP":
                        trnsys_value = 0.25
                    elif output_attribute.id == "S_PK":
                        trnsys_value = 0
                    elif output_attribute.id == "S_PK_TWE":
                        trnsys_value = 0
                    elif output_attribute.id == "m_PK":
                        trnsys_value = 0
                    elif output_attribute.id == "tA_PK":
                        trnsys_value = 50
                    else:
                        trnsys_value = 0
                    trnsys_variable_name = output_attribute.id_interface
                    sammeln_payload += f"{trnsys_variable_name} : {trnsys_value} # "

        # add trnsys full message to DataTransferComponentModel
        components.append(
            DataTransferComponentModel(
                entity_id="TRNSYS-Inputs",
                attribute_id="trnsys_sammeln",
                value=sammeln_payload,
                timestamp=datetime.now(timezone.utc),
            )
        )

        # set the current time as the new timestamp of the last output
        self.timestamp_last_output = datetime.now()

        return DataTransferModel(components=components)

    async def calibration(self, data: InputDataModel):
        """
        Function to calibrate the model - here it is possible to adjust parameters it is necessary
        Args:
            data (InputDataModel): Input data for calibration
        """
        logger.debug("Calibration of the model is not necessary for this service")
        return
