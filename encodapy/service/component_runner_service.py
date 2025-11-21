"""
Description: This module contains the definition of a service to run
    a component based on the configuration.
Author: Martin Altenburger
"""

from typing import Optional
import asyncio
from loguru import logger
from encodapy.service import ControllerBasicService
from encodapy.utils.models import (
    InputDataModel,
    InputDataEntityModel,
    InputDataAttributeModel,
    DataTransferModel,
    DataTransferComponentModel,
    AttributeTypes,
)
from encodapy.components.basic_component import (
    BasicComponent,
    ComponentValidationError
)
from encodapy.components.component_loader import get_component_class_model


class ComponentRunnerService(ControllerBasicService):
    """
    Class for a component runner service

    """

    def __init__(self, shutdown_event: Optional[asyncio.Event] = None) -> None:
        """
        Constructor for the ComponentRunnerService

        Args:
            shutdown_event (Optional[asyncio.Event]): \
                The shutdown event to signal when the service should stop
        """
        self.components: list[BasicComponent] = []
        super().__init__(shutdown_event=shutdown_event)

    def prepare_start(self):
        """ Function to prepare the service for start
        This function loads the configuration \
            and initializes the component.
        """
        for component in self.config.controller_components:

            if component.active is False:
                continue
            component_type = get_component_class_model(component.type)
            component = component_type(
                config=component, component_id=component.id, static_data=self.staticdata
            )
            self.components.append(component)

    def _result_to_input_data_attribute(
        self, result: DataTransferComponentModel
    ) -> InputDataAttributeModel:
        """
        Function to convert a DataTransferComponentModel to an InputDataAttributeModel
        """
        return InputDataAttributeModel(
            data_type=AttributeTypes.VALUE,
            id=result.attribute_id,
            data=result.value,
            unit=result.unit,
            latest_timestamp_input=result.timestamp,
            data_available=result.value is not None,
        )

    def _add_result_to_input_entity(
        self, result: DataTransferComponentModel, input_entity: InputDataEntityModel
    ) -> InputDataEntityModel:
        """
        Function to add the result of a component to an input entity, which exists.

        If the attribute already exists, it updates the attribute with the new value.
        If the attribute does not exist, it adds a new attribute to the entity.

        Args:
            result (DataTransferComponentModel): The result of the component to add
            input_entity (InputDataEntityModel): The input entity to add the result to
        Returns:
            InputDataEntityModel: The updated input entity
        """

        for attribute in input_entity.attributes:
            if result.attribute_id == attribute.id:
                attribute.data = result.value
                attribute.unit = result.unit
                logger.debug(
                    f"Update attribute: {attribute.id} with value: {result.value} "
                    f"and unit: {result.unit}"
                )

                return input_entity

        # Add a new attribute to the entity
        input_entity.attributes.append(self._result_to_input_data_attribute(result))

        return input_entity

    def add_results_to_input(
        self, data: InputDataModel, results: list[DataTransferComponentModel]
    ) -> InputDataModel:
        """
        Function to add the results of the components to the input data
        Args:
            data (InputDataModel): The input data to add the results to
            results (list[DataTransferComponentModel]): The results of the components
        Returns:
            InputDataModel: The input data with the results added
        """

        for result in results:

            for input_entity in data.input_entities:
                if input_entity.id == result.entity_id:

                    input_entity = self._add_result_to_input_entity(
                        result, input_entity
                    )
                    break

            # Add a new entity to the inputs
            data.input_entities.append(
                InputDataEntityModel(
                    id=result.entity_id,
                    attributes=[self._result_to_input_data_attribute(result)],
                )
            )

        return data

    async def calculation(self, data: InputDataModel) -> DataTransferModel:
        """
        Function to do the calculation

        Args:
            data (InputDataModel): Input data with the measured values for the calculation
        """

        all_component_results: list[DataTransferComponentModel] = []
        for component in self.components:
            try:
                component_results = component.run(data)

            except (ValueError, AttributeError, KeyError, TypeError, ComponentValidationError) as e:
                logger.error(
                    f"Error occurred while running component "
                    f"{component.component_config.id}: {e}"
                )
                continue
            all_component_results.extend(component_results)
            if component != self.components[-1]:
                self.add_results_to_input(data, component_results)

        return DataTransferModel(components=all_component_results)

    async def calibration(self, data: InputDataModel) -> None:
        """
        Function to do the calibration of the component runner service.
        This function prepares the component with the static data, \
            if this is reloaded.
        It is possible to update the static data of the component with \
            rerunning the `prepare_start_component` method with new static data.

        Args:
            data (InputDataModel): InputDataModel for the component
        """
        logger.debug("The calibration of the components has begun.")
        for component in self.components:
            component.calibrate(
                static_data=data.static_entities if self.reload_staticdata else None
            )
