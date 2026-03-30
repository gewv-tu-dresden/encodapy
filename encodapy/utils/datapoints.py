"""
Description: This module contains models for various types \
    of datapoints used in the controller component.
Author: Martin Altenburger
"""
import os
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING, TypeAlias
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
import pandas as pd
from encodapy.utils.units import DataUnits
from encodapy.utils.mediums import Medium

# Split between real imports and mock classes for Sphinx
IS_BUILDING_DOCS = "BUILDING_DOCS" in os.environ

if TYPE_CHECKING:
    # Statischer Typ für IDE/mypy
    SeriesValue: TypeAlias = pd.Series
elif IS_BUILDING_DOCS:
    # Nur für Sphinx-Importpfad
    SeriesValue: TypeAlias = Any
else:
    # Echter Runtime-Typ
    SeriesValue: TypeAlias = pd.Series

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

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        protected_namespaces=("field_", "validator_")
    )

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

class DataPointTimeSeries(DataPointGeneral):
    """
    DataPoint for time series. The value is expected to be a pandas Series 
    with a DatetimeIndex and float or integer values.
    """
    value: SeriesValue = Field(
        ...,
        description="A time series of number data points as :class:`pd.Series`",
    )
    @model_validator(mode='before')
    @classmethod
    def convert_dataframe_to_series(cls, data):
        """Convert DataFrame to Series before model validation"""
        if isinstance(data, dict) and 'value' in data:
            if isinstance(data['value'], pd.DataFrame):
                data['value'] = data['value'].squeeze()
        return data

    @field_validator('value')
    @classmethod
    def validate_time_series(cls, v: pd.Series) -> pd.Series:
        """
        Function to check, if the input is a timeseries of floats or integers

        Raises:
            ValueError: If the series does not have a DatetimeIndex\
                or if the values are not floats

        """
        if not isinstance(v.index, pd.DatetimeIndex):
            raise ValueError("Series must have a DatetimeIndex")

        if not pd.api.types.is_float_dtype(v) and not pd.api.types.is_integer_dtype(v):
            raise ValueError("Series values must be float or integer")
        return v

class DataPointDatetime(DataPointGeneral):
    """
    Model for datapoints of the controller component which define a datetime value.

    Attributes:
        value (datetime): The value of the datapoint, which is a datetime.
        unit (Optional[DataUnits]): Optional unit of the datapoint, if applicable.
        time (Optional[datetime]): Optional timestamp of the datapoint, if applicable.
    """

    value: datetime = Field(
        ...,
        description="A datetime value for the datapoint",
    )

    @field_validator('value')
    @classmethod
    def validate_datetime(cls, v: datetime) -> datetime:
        """Validate that the value is a datetime object or a string in ISO format
        that can be converted to datetime."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError as err:
                raise ValueError("String value must be in ISO format for datetime") from err
        raise ValueError("Value must be a datetime object or a string in ISO format")
