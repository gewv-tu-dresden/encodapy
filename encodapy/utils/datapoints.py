"""
Description: This module contains models for various types \
    of datapoints used in the controller component.
Author: Martin Altenburger
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from encodapy.utils.units import DataUnits
from encodapy.utils.mediums import Medium


# Models to hold the data
class DataPointGeneral(BaseModel):
    """
    Model for datapoints of the controller component.
    
    Attributes:
        value (Any): The value of the datapoint, which can be of various types \
            (string, float, int, boolean, dictionary, list, DataFrame, or None).
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Any
    unit: Optional[DataUnits] = None
    time: Optional[datetime] = None


class DataPointNumber(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Attributes:
        value (float | int): The value of the datapoint, which is a number (float, int).
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: float | int


class DataPointString(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Attributes:
        value (str): The value of the datapoint, which is a string.
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: str


class DataPointDict(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Attributes:
        value (dict): The value of the datapoint, which is a dictionary.
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: dict


class DataPointBool(DataPointGeneral):
    """
    Model for datapoints of the controller component.

    Attributes:
        value (bool): The value of the datapoint, which is a boolean.
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: bool


class DataPointMedium(DataPointGeneral):
    """
    Model for datapoints of the controller component which define the medium.

    Attributes:
        value (Medium): The value of the datapoint, which is a Medium representing the medium.
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: Medium
