"""
Defines the configuration data models for the new component.
"""

from typing import Optional, Union
from enum import Enum
from pydantic import Field, field_validator, model_validator
import pandas as pd
import flixopt as fx # type: ignore[import-untyped]
from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber
from encodapy.utils.units import DataUnits

class DataPointTimeSeries(DataPointGeneral):
    """
    DataPoint for time series with general float values
    """
    value: pd.Series= Field(
        ...,
        description="A time series of general data points",
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
        Function to check, if the input is a timeseries of floats

        Raises:
            ValueError: If the series does not have a DatetimeIndex\
                or if the values are not floats

        """
        if not isinstance(v.index, pd.DatetimeIndex):
            raise ValueError("Series must have a DatetimeIndex")

        if not pd.api.types.is_float_dtype(v) and not pd.api.types.is_integer_dtype(v):
            raise ValueError("Series values must be float or integer")
        return v
class FlixoptComponentInputData(InputData):
    """
    Input model for the Flixopt component
    """

    electricity_demand: DataPointTimeSeries = Field(
        ...,
        description="""The electricity demand input as a time series""",
        json_schema_extra={"unit": "WHR"}
    )
    heat_demand: DataPointTimeSeries = Field(
        ...,
        description="The heat demand input as a time series",
        json_schema_extra={"unit": "WHR"},
    )
    electricity_price: DataPointTimeSeries = Field(
        ...,
        description="The electricity price input as a time series",
        # json_schema_extra={"unit": "EUR"}, #TODO define unit for price
    )


class FlixoptComponentOutputData(OutputData):
    """
    Output model for the Flixopt component
    """

    boiler_heat_output: DataPointGeneral = Field(
        ...,
        description="The heat output time series from the boiler",
        json_schema_extra={"unit": "WHR"},
    )
    chp_heat_output: DataPointTimeSeries = Field(
        ...,
        description="The heat output time series from the chp",
        json_schema_extra={"unit": "WHR"},
    )
    chp_electric_output: DataPointTimeSeries = Field(
        ...,
        description="The electric output time series from the chp",
        json_schema_extra={"unit": "WHR"},
    )
    thermal_storage_charge_state: DataPointTimeSeries = Field(
        ...,
        description="The charge state time series from the thermal storage",
        json_schema_extra={"unit": "WHR"},
    )

    # result: DataPointGeneral = Field(
    #     ...,
    #     description="Result of the new component",
    #     json_schema_extra={"unit": "CEL"},
    # )
    # optional_result: Optional[DataPointGeneral] = Field(
    #     ...,
    #     description="""This is an optional result of the new component
    #     and does not need to be exported.""",
    #     json_schema_extra={"unit": "CEL"},
    # )

class FlixoptLogLevel(Enum):
    """
    Log-Levels from flixopt configuration - see: flixopt.CONFIG 
    
    FLIXOPT_CONFIG_MAP is used to map the enum values \
        to the actual flixopt configuration functions

    """
    EXPLORING = "exploring"
    DEBUG = "debug"
    PRODUCTION = "production"
    SILENT = "silent"

FLIXOPT_CONFIG_MAP = {
    FlixoptLogLevel.EXPLORING: fx.CONFIG.exploring,
    FlixoptLogLevel.DEBUG: fx.CONFIG.debug,
    FlixoptLogLevel.PRODUCTION: fx.CONFIG.production,
    FlixoptLogLevel.SILENT: fx.CONFIG.silent,
}
class DataPointFlixoptLogLevel(DataPointGeneral):
    """
    DataPoint for Flixopt log level
    """
    value: FlixoptLogLevel = Field(
        FlixoptLogLevel.SILENT,
        description="Log level for the flixopt framework",
    )
    @model_validator(mode='before')
    @classmethod
    def lowercase_to_enum(cls, data):
        """Convert lowercase string to FlixoptLogLevel enum before model validation"""
        if isinstance(data, dict) and 'value' in data:
            if isinstance(data['value'], str):
                data['value'] = data['value'].lower()
        return data

class FlixoptComponentConfigData(ConfigData):
    """
    Config data model for the FlixOpt component
    """

    flixopt_log_level: DataPointFlixoptLogLevel = Field(
        default=DataPointFlixoptLogLevel.model_validate({}),
        description="Log level for the flixopt framework",
    )
