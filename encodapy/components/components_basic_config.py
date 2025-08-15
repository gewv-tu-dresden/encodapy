"""
Basic configuration for the components in the Encodapy framework.
Author: Martin Altenburger
"""

from typing import Dict, List, Optional, Union
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict, Field, RootModel
from encodapy.utils.units import DataUnits


class IOAllocationModel(BaseModel):
    """
    Model for the input or output allocation.

    Contains:
        `entity`: ID of the entity to which the input or output is allocated
        `attribute`: ID of the attribute to which the input or output is allocated
    """

    entity: str = Field(
        ..., description="ID of the entity to which the input or output is allocated"
    )
    attribute: str = Field(
        ..., description="ID of the attribute to which the input or output is allocated"
    )


class IOModell((RootModel[Dict[str, IOAllocationModel]])):  # pylint: disable=too-few-public-methods
    """
    Model for the input, staticdata and output of a component.
    """


class ControllerComponentModel(BaseModel):
    """
    Model for the configuration of the controller components.
    Contains:
    - active: Whether the component is active or not
    - id: The id of the component
    - type: The type of the component (e.g. thermal storage, heat pump, etc. / \
        needs to be defined for individual components)
    - inputs: The inputs of the component as a dictionary with IOAllocationModel \
        for the individual inputs
    - outputs: The outputs of the component as a dictionary with IOAllocationModel \
        for the individual outputs
    - staticdata: The static data of the component as a dictionary with IOAllocationModel \
        for the individual static data
    - config: The configuration of the component as a dictionary
    
    """

    active: Optional[bool] = True
    id: str
    type: str
    inputs: IOModell
    outputs: IOModell
    staticdata: Optional[IOModell] = None
    config: dict


class ControllerComponentStaticDataAttribute(BaseModel):
    """
    Model for the static data attributes of the controller component.
    
    Contains:
        value: The value of the static data attribute, which can be of various types \
            (string, float, int, boolean, dictionary, list, DataFrame, or None)
        unit: Optional unit of the static data attribute, if applicable
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Union[str, float, int, bool, dict, List, DataFrame, None]
    unit: Optional[DataUnits] = None


class ControllerComponentStaticData(  # pylint: disable=too-few-public-methods
    RootModel[Dict[str, ControllerComponentStaticDataAttribute]]
):
    """
    Model for the static data of the controller.
    
    Contains:
        - root: The static data as a dictionary with the key as the ID of the static data \
            (like in the config) and the value as the value of the static data.
    """
