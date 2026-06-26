"""
Defines the configuration data models for the new component.
"""

from typing import Optional
from enum import Enum
from pydantic import Field, field_validator, model_validator, BaseModel, ConfigDict
import pandas as pd
import flixopt as fx # type: ignore[import-untyped]
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
class FlixoptExampleComponentInputData(InputData):
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


class FlixoptExampleComponentOutputData(OutputData):
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

class FlixOptSolverName(Enum):
    """
    Names of the available Flixopt solvers
    
    See flixopt.solvers for available solvers
    """
    GUROBI = "GurobiSolver"
    HIGHS = "HighsSolver"

class FlixoptSolverSettings(BaseModel):
    """
    Base model for Flixopt solver settings.
    Only non-None values override the flixopt defaults.
    """
    name: FlixOptSolverName = Field(
        ...,
        description="Name of the solver (e.g. 'HighsSolver' or 'GurobiSolver')",
    )
    mip_rel_gap: Optional[float] = Field(
        default=None,
        description="Optional relative optimality gap in [0.0, 1.0]",
    )
    time_limit: Optional[int] = Field(
        default=None,
        description="Optional time limit in seconds",
    )

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

class FlixoptExampleComponentConfigData(ConfigData):
    """
    Config data model for the FlixOpt component
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

class FlixOptEffects(BaseModel):
    """
    Model to hold the flixopt Effects used in the component
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    costs: fx.Effect = Field(
        ...,
        description="Effect model for costs in the flixopt model",
    )
    co2: fx.Effect = Field(
        ...,
        description="Effect model for CO2 emissions in the flixopt model",
    )
    pe: fx.Effect = Field(
        ...,
        description="Effect model for primary energy consumption in the flixopt model",
    )
