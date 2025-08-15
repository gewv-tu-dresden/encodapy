"""
This module provides basic components for the encodapy package.
"""

from typing import Dict, List, Optional, Union

from loguru import logger
from pandas import DataFrame
from pydantic import ValidationError

from encodapy.components.components_basic_config import (
    ControllerComponentModel,
    ControllerComponentStaticData,
    ControllerComponentStaticDataAttribute,
    IOAllocationModel,
    IOModell,
)
from encodapy.utils.models import DataUnits, InputDataEntityModel, StaticDataEntityModel


class BasicComponent:
    """
    Base class for all components in the encodapy package.
    This class provides basic functionality that can be extended by specific components.

    Contains methods for:
    - Getting component configuration: `get_component_config()`
    - Getting input values: `get_component_input()`
    - Setting all static data of the component: `set_component_static_data()`
    - Getting static data (by id): `get_component_static_data()`

    Args:
        config (Union[ControllerComponentModel, list[ControllerComponentModel]]):
            Configuration of the component or a list of configurations.
        component_id (str): ID of the component to get the configuration for.
        reload_static_data (bool): Flag to indicate if static data should be reloaded.
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        if isinstance(config, ControllerComponentModel):
            self.component_config = ControllerComponentModel.model_validate(config)
        else:
            self.component_config = ControllerComponentModel.model_validate(
                self.get_component_config(config=config, component_id=component_id)
            )

        self.static_data = ControllerComponentStaticData({})
        self.set_component_static_data(
            static_data, static_config=self.component_config.staticdata
        )

    def get_component_config(
        self, config: list[ControllerComponentModel], component_id: str
    ) -> ControllerComponentModel:
        """
        Function to get the configuration of a specific component from the service configuration
        Args:
            config (list[ControllerComponentModel]): List of all components in the configuration
            component_id (str): ID of the component to get the configuration
        Returns:
            ControllerComponentModel: Configuration of the component by ID

        Raises:
            ValueError: If the component with the given ID is not found in the configuration
        """
        for component in config:
            if component.id == component_id:
                return component
        raise ValueError(f"No component configuration found for {component_id}")

    def get_component_input(
        self,
        input_entities: Union[list[InputDataEntityModel], list[StaticDataEntityModel]],
        input_config: IOAllocationModel,
    ) -> tuple[
        Union[str, float, int, bool, Dict, List, DataFrame, None],
        Union[DataUnits, None],
    ]:
        """
        Function to get the value of the input data for a spesific input configuration \
            of a component of the controller (or a inividual one).

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (IOAllocationModel): Configuration of the input

        Returns:
        """

        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return attribute.data, attribute.unit

        raise ValueError(f"Input data {input_config.entity} not found")

    def set_component_static_data(
        self,
        static_data: Union[list[StaticDataEntityModel], None],
        static_config: Union[IOAllocationModel, IOModell, None],
    ):
        """
        Function to get the value of the static data for a spesific input configuration \
            of a component of the controller (or a inividual one).

        Args:
            static_data (Union[list[StaticDataEntityModel], None]): Data of static entities
            static_config (Union[IOAllocationModel, IOModell, None]): \
                Configuration of the static data

        """

        if static_config is None:
            logger.debug("No static config provided, skipping static data setup.")
            return

        if static_data is None:
            logger.warning("The component's static data could not be set: "
                           "static_data is None.")
            return
            # Do not overwrite the static data if not data is available or no static config is given

        static_config_data = {}
        number_static_datapoints = 0

        if isinstance(static_config, IOModell):
            for static_config_item in static_config.root.keys():
                datapoint_value, datapoint_unit = self.get_component_input(
                    input_entities=static_data,
                    input_config=static_config.root[static_config_item],
                )
                static_config_data[static_config_item] = (
                    ControllerComponentStaticDataAttribute(
                        value=datapoint_value, unit=datapoint_unit
                    )
                )
                number_static_datapoints += 1
        elif isinstance(static_config, IOAllocationModel):
            datapoint_value, datapoint_unit = self.get_component_input(
                input_entities=static_data,
                input_config=static_config,
            )
            static_config_data[static_config.entity] = (
                ControllerComponentStaticDataAttribute(
                    value=datapoint_value, unit=datapoint_unit
                )
            )
            number_static_datapoints += 1
        else:
            raise ValueError("Unsupported static config type")
        try:
            static_data_model = ControllerComponentStaticData.model_validate(
                static_config_data
            )
        except ValidationError as error:
            logger.error(f"Error in static data configuration: {error}"
                         " Could not validate and set the static data model")
            return

        static_config_available = len(static_data_model.root.keys()) == number_static_datapoints

        if not static_config_available:
            logger.error(
                "Static data configuration does not match the component configuration. "
                "Please check the configuration."
            )
            return
        self.static_data = static_data_model

    def get_component_static_data(
        self,
        component_id: str,
        unit: Optional[DataUnits] = None
    ) -> Union[str, float, int, bool, Dict, List, DataFrame, None]:
        """
        Function to get the static data of a component by its ID \
            and in the specified unit (optional).
        Args:
            component_id (str): ID of the component to get the static data for
            unit (Optional[str]): Unit to convert the static data value to, if specified
        Returns:
            Union[str, float, int, bool, Dict, List, DataFrame, None]: 
                The value of the static data in the specified unit or as is if no unit is specified
        """
        if component_id not in self.static_data.root.keys():
            return None

        static_data = ControllerComponentStaticDataAttribute.model_validate(
            self.static_data.root.get(component_id, None)
        )
        static_data_value = static_data.value
        static_data_unit = static_data.unit

        if unit is not None and static_data_unit is not None:
            if static_data_unit == unit:
                return static_data_value
            # TODO: Implement unit conversion if needed
            raise ValueError(
                f"Unit conversion from {static_data_unit} to {unit} is not implemented"
            )

        return static_data_value
