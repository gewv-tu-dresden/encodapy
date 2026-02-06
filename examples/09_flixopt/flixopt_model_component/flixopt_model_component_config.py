"""
Defines the configuration data models for the new component.
"""
from typing import Any
import pandas as pd
from pydantic import Field, model_validator, field_validator, ConfigDict
import flixopt as fx # type: ignore[import-untyped]
from .flixopt_models import (
    FlixOptSolverName,
    FlixoptSolverSettings,
    FlixoptLogLevel
)
from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber

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

class FlixoptModelComponentInputData(InputData):
    """
    Input model for the Flixopt model component

    The `model_config` field is set to allow flexible input of model parameters, 
    so the required parameters can be defined in the flixopt model itself.
    This way, the component can be used with different flixopt models 
    without needing to change the input data model.
    """
    model_config = ConfigDict(
        extra="allow"
    )



class FlixoptModelComponentOutputData(OutputData):
    """
    Output model for the Flixopt model component
    
    The `model_config` field is set to allow flexible output of model parameters, 
    so the output parameters can be defined in the flixopt model itself.

    The component provide this output variables:
    - Storage levels for all storages in the model like this: `{storage_label}_soc`
    - For all converters in the model, the thermal power like this: \
        `{converter_label}_thermal_power`
    - For all CHP converters in the model, the electrical power like this: \
        `{converter_label}_electrical_power`
    """
    model_config = ConfigDict(
        extra="allow"
    )



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


class DataPointFlixoptSolverSettings(DataPointGeneral):
    """
    DataPoint for Flixopt solver settings.
    Leaves solver parameters unset so flixopt can use its own defaults.
    """
    value: FlixoptSolverSettings = Field(
        default=FlixoptSolverSettings(
            name=FlixOptSolverName.HIGHS,
            mip_rel_gap=None,
            time_limit=None,
        ),
        description="Solver settings for the flixopt framework",
    )

class FlixoptModelComponentConfigData(ConfigData):
    """
    Config data model for the FlixOpt model component
    """

    log_level: DataPointFlixoptLogLevel = Field(
        default=DataPointFlixoptLogLevel.model_validate({}),
        description="Log level for the flixopt framework",
    )
    solver_settings: DataPointFlixoptSolverSettings = Field(
        default = DataPointFlixoptSolverSettings.model_validate({}),
        description="Solver settings for the flixopt framework",
    )
    excess_penalty: DataPointNumber = Field(
        default=DataPointNumber.model_validate({
            "value": 1e5
        }),
        description="Penalty cost for excess of limits in the flixopt model",
    )

    def get_solver(self) -> fx.solvers._Solver:
        """
        Build the configured solver.
        Only forwards parameters explicitly set in the config; otherwise
        flixopt uses its own defaults from CONFIG.Solving.
        """
        # pylint: disable=no-member
        solver_name = self.solver_settings.value.name.value
        solver_cls = getattr(fx.solvers, solver_name, None)
        if solver_cls is None:
            raise ValueError(f"Unsupported solver name: {solver_name}")
        # pylint: disable=no-member
        cfg = self.solver_settings.value
        kwargs = {}
        if cfg.mip_rel_gap is not None:
            kwargs["mip_gap"] = cfg.mip_rel_gap
        if cfg.time_limit is not None:
            kwargs["time_limit_seconds"] = cfg.time_limit

        return solver_cls(**kwargs)
