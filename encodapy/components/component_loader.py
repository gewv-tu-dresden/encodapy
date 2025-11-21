"""
Description: This module provides functions to load component models and configurations.
Author: Martin Altenburger
"""

import importlib
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, Union, cast

from loguru import logger
from pydantic import BaseModel, Field, create_model

from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    IOAllocationModel,
    OutputData,
)

if TYPE_CHECKING:
    from encodapy.components.basic_component import BasicComponent


class ModelTypes(Enum):
    """
    Enumeration of model types for components.
    """

    COMPONENT = "component"
    COMPONENT_CONFIG = "component_config"


def check_component_type(component_type: str):
    """
    Check the component type and return the component type and path.
    If the component type is not fully qualified, return None for the path.
    """
    if "." not in component_type:
        return component_type, None

    component_type_name = component_type.rsplit(".", 1)[-1]
    component_type_path = ".".join(
        [p.strip(".") for p in (component_type, component_type_name)]
    )
    return component_type_name, component_type_path


def get_component_model(
    component_type: str,
    model_type: Optional[ModelTypes],
    model_subname: Optional[str] = None,
    none_allowed: bool = False,
) -> Union[Type["BaseModel"], Type["BasicComponent"], None]:
    """
    Function to get the model information for the component.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module, \
            if not part of EnCoDaPy. Defaults to None.

    Returns:
        Union[Type["BaseModel"], Type["BasicComponent"], None]: \
            The model if found
    """

    component_type, module_base_path = check_component_type(component_type)

    if module_base_path is None:
        module_base_path = f"encodapy.components.{component_type}.{component_type}"

    if model_type is ModelTypes.COMPONENT:
        module_path = module_base_path
    elif model_type is ModelTypes.COMPONENT_CONFIG:
        module_path = f"{module_base_path}_config"
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    try:
        config_module = importlib.import_module(module_path)
    except ImportError as e:
        logger.error(f"Error importing module {module_path}: {e}")
        return None

    model_name = "".join(part.capitalize() for part in component_type.split("_"))

    model_name = model_name if model_subname is None else f"{model_name}{model_subname}"

    try:
        class_model = getattr(config_module, model_name)
        return class_model
    except AttributeError:
        error_msg = f"Class model '{model_name}' not found in {config_module.__name__}"
        if none_allowed:
            logger.debug(error_msg)
            return None
        logger.error(error_msg)
    raise AttributeError(error_msg)


def get_component_class_model(component_type: str) -> "Type[BasicComponent]":
    """Get the component class model for a specific component type.

    Args:
        component_type (str): Type of the component
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Type[BasicComponent]: The component class model
    """
    module = importlib.import_module("encodapy.components.basic_component")
    basic_component_class = getattr(module, "BasicComponent")

    component_class = get_component_model(
        component_type=component_type,
        model_type=ModelTypes.COMPONENT,
    )

    if component_class is None:
        raise KeyError(f"Component class not found for {component_type}")
    if issubclass(component_class, basic_component_class):
        return cast("Type[BasicComponent]", component_class)

    error_msg = f"Component class {component_class.__name__} is not a subclass of BasicComponent"
    logger.error(error_msg)
    raise TypeError(error_msg)


def get_component_io_model(
    component_type: str, model_subname: str
) -> Union[Type[InputData], Type[OutputData]]:
    """Get the component io (input or output) model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_name (Optional[str], optional): Name of the Type of the model.
        module_path (Optional[str], optional): Path to the module. \
            Required if not part of EnCoDaPy. Defaults to None.

    Returns:
        Union[Type[InputData], Type[OutputData]]: The component io model with the model subname
    """
    component_data_model = get_component_model(
        component_type=component_type,
        model_subname=model_subname,
        model_type=ModelTypes.COMPONENT_CONFIG,
    )

    if component_data_model is None:
        raise KeyError(f"Component Config Model not found for {component_type}")

    if not issubclass(component_data_model, (InputData, OutputData)):
        error_msg = (
            f"Component class {component_data_model.__name__} "
            "is not a subclass of BaseModel"
        )
        logger.error(error_msg)
        raise TypeError(error_msg)

    # 1. Create the fields for the new model
    fields: Dict[str, Tuple[Any, Any]] = {}
    for datapoint_name, datapoint_info in component_data_model.model_fields.items():
        fields[datapoint_name] = (
            (
                IOAllocationModel
                if datapoint_info.is_required()
                else Optional[IOAllocationModel]
            ),
            Field(
                default=None if not datapoint_info.is_required() else ...,
                description=datapoint_info.description,
                json_schema_extra=datapoint_info.json_schema_extra,
            ),
        )

    # 2. Create the new model dynamically
    component_config_model = create_model(
        f"IO_{component_data_model.__name__}",
        **cast(Dict[str, Any], fields),
        __base__=component_data_model,
    )
    # 3. copy methods (if any)
    for attr_name, attr_value in component_data_model.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            setattr(component_config_model, attr_name, attr_value)

    # 4. copy validators (if any)
    for name, validator in component_data_model.__dict__.items():
        if hasattr(validator, "__validator_function__"):
            setattr(component_config_model, name, validator)

    return cast(Union[Type[InputData], Type[OutputData]], component_config_model)


def get_component_data_model(
    component_type: str,
    model_subname: str,
    data_model_type: Union[Type[InputData], Type[OutputData], Type[ConfigData]],
    none_allowed=True,
) -> Union[Type[InputData], Type[OutputData], Type[ConfigData], None]:
    """
    Get the component data model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_subname (str): Subname of the model
        data_model_type (Union[Type[InputData], Type[OutputData], Type[ConfigData]]): \
            Type of the data model
        none_allowed (bool, optional): Whether None is allowed as a return value. \
            Defaults to True.

    Raises:
        KeyError: If the component data model is not found.
        TypeError: If the component data model is not of the expected type.

    Returns:
        Union[Type[InputData], Type[OutputData], Type[ConfigData], None]: \
            The component data model or None if not found.
    """
    data_model = get_component_model(
        component_type=component_type,
        model_subname=model_subname,
        model_type=ModelTypes.COMPONENT_CONFIG,
        none_allowed=True,
    )

    if data_model is None:
        if none_allowed:
            logger.debug(f"No data model found for {component_type}")
            return None
        raise KeyError(f"Component Config Model not found for {component_type}")
    if not issubclass(data_model, data_model_type):
        error_message = (
            f"Component class {data_model.__name__} "
            f"is not a subclass of {data_model_type.__name__}"
        )
        logger.error(error_message)
        raise TypeError(error_message)
    return cast(Union[Type[InputData], Type[OutputData], Type[ConfigData]], data_model)


def get_component_config_data_model(
    component_type: str, model_subname: str
) -> Union[Type[ConfigData], None]:
    """Get the component config data model for a specific component type.

    Args:
        component_type (str): Type of the component
        model_subname (Optional[str], optional): Name of the Type of the model.

    Returns:
        Union[Type[BasicComponent], None]: The component static data model or None, if not found.
    """
    return cast(
        Optional[Type[ConfigData]],
        get_component_data_model(
            component_type=component_type,
            model_subname=model_subname,
            data_model_type=ConfigData,
            none_allowed=True,
        ),
    )


def get_component_input_data_model(component_type: str) -> Type[InputData]:
    """Get the component input data model for a specific component type.

    Args:
        component_type (str): Type of the component

    Returns:
        Type[InputData]: The component input data model.
    """
    return cast(
        Type[InputData],
        get_component_data_model(
            component_type=component_type,
            model_subname="InputData",
            data_model_type=InputData,
        ),
    )


def get_component_output_data_model(component_type: str) -> Type[OutputData]:
    """Get the component output data model for a specific component type.

    Args:
        component_type (str): Type of the component

    Returns:
        Type[OutputData]: The component output data model.
    """
    return cast(
        Type[OutputData],
        get_component_data_model(
            component_type=component_type,
            model_subname="OutputData",
            data_model_type=OutputData,
        ),
    )
