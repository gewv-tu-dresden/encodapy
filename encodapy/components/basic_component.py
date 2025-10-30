"""
Description: This module provides basic components for the encodapy package.
Author: Martin Altenburger
"""

from datetime import datetime, timezone
from typing import Any, Optional, Type, Union, TypeVar, Generic, cast
from loguru import logger
from pydantic import ValidationError
from encodapy.components.basic_component_config import (
    ComponentIOModel,
    ComponentValidationError,
    ConfigData,
    ConfigDataPoints,
    ControllerComponentModel,
    DataPointGeneral,
    InputData,
    IOAllocationModel,
    IOModell,
    OutputData,
)
from encodapy.components.component_loader import (
    get_component_config_data_model,
    get_component_input_data_model,
    get_component_io_model,
    get_component_output_data_model,
)
from encodapy.utils.models import (
    DataTransferComponentModel,
    InputDataEntityModel,
    InputDataModel,
    StaticDataEntityModel,
)

# Type variables for component data models
# - these are used for type hinting in the BasicComponent class
TypeConfigData = TypeVar(
    "TypeConfigData", bound=ConfigData
)  # pylint: disable=invalid-name
TypeInputData = TypeVar(
    "TypeInputData", bound=InputData
)  # pylint: disable=invalid-name
TypeOutputData = TypeVar(
    "TypeOutputData", bound=OutputData
)  # pylint: disable=invalid-name


class BasicComponent(Generic[TypeConfigData, TypeInputData, TypeOutputData]):
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
        static_data (Optional[list[StaticDataEntityModel]]): Static data for the component.
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

        self.config_data: TypeConfigData
        self.set_component_config_data(
            static_data=static_data, static_config=self.component_config.config
        )
        # Inputs and Outputs of the component itself
        self.io_model: Optional[ComponentIOModel] = None
        self.input_data: TypeInputData
        self.output_data: TypeOutputData

        self._prepare_i_o_config()

        self.prepare_component()

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

        raise KeyError(f"No component configuration found for {component_id}")

    def _get_input_and_output_config_models(
        self,
    ) -> tuple[Type[InputData], Type[OutputData]]:
        """
        Function to get the input and output models for the component.
        There needs to be a InputModel and a OutputModel in the config-module for the component.

        """
        component_input_model = get_component_io_model(
            component_type=self.component_config.type, model_subname="InputData"
        )
        component_output_model = get_component_io_model(
            component_type=self.component_config.type, model_subname="OutputData"
        )

        if not (
            issubclass(component_input_model, InputData)
            and issubclass(component_output_model, OutputData)
        ):
            error_msg = "Input or output model is not a subclass of BaseModel"
            logger.error(error_msg)
            raise TypeError(error_msg)

        return component_input_model, component_output_model

    def _prepare_i_o_config(self):
        """
        Function to prepare the I/O configuration for the component
        """
        component_input_model, component_output_model = (
            self._get_input_and_output_config_models()
        )
        config = self.component_config
        try:
            input_config = component_input_model.model_validate(
                config.inputs.root
                if isinstance(config.inputs, IOModell)
                else config.inputs
            )
        except ValidationError:
            error_msg = f"Invalid input configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        try:
            output_config = component_output_model.model_validate(
                config.outputs.root
                if isinstance(config.outputs, IOModell)
                else config.outputs
            )
        except ValidationError:
            error_msg = f"Invalid output configuration for the component {self.component_config.id}"
            logger.error(error_msg)
            raise

        self.io_model = ComponentIOModel(input=input_config, output=output_config)

    def set_component_config_data(
        self,
        static_data: Union[list[StaticDataEntityModel], None],
        static_config: Optional[ConfigDataPoints] = None,
    ):
        """
        Function to get the value of the static data for a specific input configuration \
            of a component of the controller (or a individual one).

        Args:
            config_data (Union[list[StaticDataEntityModel], None]): Data of static entities
            static_config (Optional[ConfigDataPoints]): \
                Configuration of the static data, if available
                
        Raises:
            ComponentValidationError: If the static data configuration is invalid.

        """
        try:
            assert (
                static_config is not None
            ), "No static config provided, skipping static data setup."
            assert isinstance(
                static_config, ConfigDataPoints
            ), "Invalid static config provided."
        except AssertionError as e:
            logger.error(f"Static config error: {e}")
            raise ComponentValidationError(f"Static config error: {e}") from e

        config_model = get_component_config_data_model(
            component_type=self.component_config.type, model_subname="ConfigData"
        )

        if config_model is None:
            logger.debug("No config model found, skipping static config check.")
            return

        static_config_data: dict[str, DataPointGeneral] = {}

        for datapoint_name, _ in config_model.model_fields.items():
            if datapoint_name not in static_config.root:
                logger.debug(
                    f"Static config {datapoint_name} not in static configuration, "
                    "trying to skip it."
                )
                continue
            datapoint = static_config.root[datapoint_name]

            if isinstance(datapoint, DataPointGeneral):
                static_config_data[datapoint_name] = datapoint

            if isinstance(datapoint, IOAllocationModel):
                if static_data is None:
                    error_msg = (
                        f"Config entry '{datapoint_name}' needs static data but its not provided "
                        f"to the component {self.component_config.id}."
                    )
                    logger.error(error_msg)
                    raise ComponentValidationError(error_msg)
                static_config_data[datapoint_name] = self.get_component_input(
                    input_entities=static_data, input_config=datapoint
                )

        # we need to convert the data to a dict of the correct types
        # because the config data model could contain different types
        static_config_raw: dict[str, Any] = {}
        for key, value in static_config_data.items():
            static_config_raw[key] = value.model_dump()

        try:
            self.config_data = cast(
                TypeConfigData, config_model.model_validate(static_config_raw)
            )

        except ValidationError as error:
            error_msg = (
                f"Error in static data configuration: {error}"
                " Could not validate and set the static data model"
            )
            logger.error(error_msg)
            raise ComponentValidationError(error_msg) from error

    def get_component_input(
        self,
        input_entities: Union[
            list[InputDataEntityModel],
            list[StaticDataEntityModel],
            list[Union[InputDataEntityModel, StaticDataEntityModel]],
        ],
        input_config: IOAllocationModel,
    ) -> DataPointGeneral:
        """
        Function to get the value of the input data for a specific input configuration \
            of a component of the controller (or a individual one).

        Args:
            input_entities (list[InputDataEntityModel]): Data of input entities
            input_config (IOAllocationModel): Configuration of the input

        Returns:
            DataPointGeneral: The value of the input data and its unit and timestamp
        """
        for input_data in input_entities:
            if input_data.id == input_config.entity:
                for attribute in input_data.attributes:
                    if attribute.id == input_config.attribute:
                        return DataPointGeneral(
                            value=attribute.data,
                            unit=attribute.unit,
                            time=attribute.latest_timestamp_input,
                        )

        raise KeyError(
            f"Input data {input_config.entity} / {input_config.attribute} not found. "
            "Please check the configuration of the Inputs, Outputs and Static Data."
        )

    def set_input_data(self, input_data: InputDataModel) -> None:
        """
        Set the input values for the component from the provided input entities.
        The input values are extracted based on the component's input configuration.
        Also static data is used as input.

        Input data is validated against the component's input model and stored in self.input_data.

        The validation ensures that the input data conforms to the expected structure and types.
        Also the units are checked and converted if necessary.

        Args:
            input_data (InputDataModel): Input data model containing all necessary entities

        """
        if self.io_model is None:
            return
        # use all input datapoints, also the static data (flexible solution)
        input_datapoints: list[Union[InputDataEntityModel, StaticDataEntityModel]] = []
        input_datapoints.extend(input_data.input_entities)
        input_datapoints.extend(input_data.static_entities)

        input_values: dict[str, DataPointGeneral] = {}

        input_data_model = get_component_input_data_model(
            component_type=self.component_config.type
        )
        for datapoint_name, datapoint_config in self.io_model.input.__dict__.items():
            if datapoint_config is None:
                continue
            try:
                datapoint_config = IOAllocationModel.model_validate(datapoint_config)
            except ValidationError as e:
                logger.warning(
                    f"Invalid input configuration for {datapoint_name} "
                    f"in {self.component_config.id}: {e}"
                )
                continue

            datapoint = self.get_component_input(
                input_entities=input_datapoints, input_config=datapoint_config
            )

            # Skip optional datapoints with no value
            if (
                not input_data_model.model_fields[datapoint_name].is_required()
                and datapoint.value is None
            ):
                continue
            input_values[datapoint_name] = datapoint

        input_values_raw: dict[str, Any] = {}
        for key, value in input_values.items():
            input_values_raw[key] = value.model_dump()

        self.input_data = cast(
            TypeInputData, input_data_model.model_validate(input_values_raw)
        )

    def prepare_component(self):
        """
        Function to prepare the component.
        This function should be implemented in each component to prepare the component.
        """
        logger.debug(
            "Prepare component is not implemented in the base class"
            f" for {self.component_config.id}"
        )

    def calculate(self):
        """
        Function to calculate the output of the component.
        This function should be implemented in each component to calculate the output.

        The function should use the input data stored in self.input_data
        and the static data stored in self.config_data to perform the calculation.
        The result should be stored in self.output_data.

        Raises:
            ValueError: If the calculation fails due to invalid input data.
            KeyError: If a required input data point is missing.
            RuntimeError: If the calculation cannot be performed for other reasons.
        """
        logger.debug(
            "Calculate is not implemented in the base class"
            f" for {self.component_config.id}"
        )

    def run(self, data: InputDataModel) -> list[DataTransferComponentModel]:
        """
        Run the component.
        
        Args:
            data (InputDataModel): Input data for the component, \
                including all necessary entities.
        Returns:
            list[DataTransferComponentModel]: List of data transfer components.
        """
        components: list[DataTransferComponentModel] = []

        if self.io_model is None:
            logger.warning(f"IOModel of {self.component_config.id} is not set.")
            return components

        try:
            self.set_input_data(input_data=data)
        except (ValueError, KeyError) as e:
            logger.error(
                f"Setting input data failed for {self.component_config.id}: {e}"
            )
            return components

        try:
            self.calculate()
        except (ValueError, KeyError, RuntimeError) as e:
            logger.error(f"Calculation failed for {self.component_config.id}: {e}")
            return components

        try:
            output_model = get_component_output_data_model(
                component_type=self.component_config.type
            )

            if not hasattr(self, "output_data"):
                raise ValueError("Output data is not set in the component.")

            self.output_data = cast(
                TypeOutputData,
                output_model.model_validate(self.output_data.model_dump()),
            )

        except KeyError as e:
            logger.error(
                f"Getting output model failed for {self.component_config.id}: {e}"
            )
            return components
        except (ValidationError, ValueError) as e:
            logger.error(
                f"Output validation failed for {self.component_config.id}: {e}"
            )
            return components

        for datapoint_name, datapoint_config in self.io_model.output.__dict__.items():
            if datapoint_config is None:
                continue
            try:
                datapoint_config = IOAllocationModel.model_validate(datapoint_config)
                datapoint = DataPointGeneral.model_validate(
                    getattr(self.output_data, datapoint_name, None)
                )
            except ValidationError as e:
                logger.error(
                    f"Validating datapoint config failed for {datapoint_name} "
                    f"of {self.component_config.id}: {e}"
                )
                continue

            components.append(
                DataTransferComponentModel(
                    entity_id=datapoint_config.entity,
                    attribute_id=datapoint_config.attribute,
                    value=datapoint.value,
                    unit=datapoint.unit,
                    timestamp=datapoint.time or datetime.now(timezone.utc),
                )
            )

            logger.debug(
                f"Calculated {datapoint_name}: {datapoint.value} {datapoint.unit} "
                f"for {self.component_config.id}."
            )

        return components

    def calibrate(
        self,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ):
        """
        Calibrate the component
        - This function updates the static data \
            and prepares the component for operation with the new static data
        - This function can be used to adjust parameters of the component, \
            so it needs to be extended
        Args:
            static_data (Optional[list[StaticDataEntityModel]]): Static data for the component
        """
        if static_data is not None:
            try:
                logger.debug(
                    f"Reloading static data for the component {self.component_config.id}"
                )
                self.set_component_config_data(
                    static_data=static_data, static_config=self.component_config.config
                )
                self.prepare_component()
            except ComponentValidationError as e:
                logger.error(
                    f"Failed to reload static data for {self.component_config.id}: {e}"
                )
                raise
