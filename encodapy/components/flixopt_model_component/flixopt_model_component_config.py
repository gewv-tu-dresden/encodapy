"""
Defines the configuration data models for the new component.
"""
from typing import Any, cast
from pydantic import Field, model_validator, ConfigDict
import flixopt as fx # type: ignore[import-untyped]
from encodapy.components.basic_component_config import (
    ConfigData,
    InputData,
    OutputData,
)
from encodapy.utils.datapoints import DataPointGeneral, DataPointNumber
from encodapy.components.flixopt_model_component.flixopt_models import (
    FlixOptSolverName,
    FlixoptSolverSettings,
    FlixoptLogLevel
)



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
            threads=None,
            mip_focus=None,
            heuristics=None,
            presolve=None,
            cuts=None,
            additional_options=None,
        ),
        description="Solver settings for the flixopt framework",
    )
class DataPointFlixoptModelConfig(DataPointGeneral):
    """
    DataPoint for Flixopt model configuration.
    Can be a dict or a path to a json file.
    """
    value: dict[str, Any]|str = Field(
        ...,
        description="Flixopt model configuration as dict or a path to a json file",
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
    flixopt_model: DataPointFlixoptModelConfig = Field(
        ...,
        description="""
        Flixopt model configuration as dict or a path to a json file as ``DataPointFlixoptModelConfig``.
        Default to None. A valid flixopt model configuration must be provided.
        """
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
        kwargs: dict[str, Any] = {}
        if cfg.mip_rel_gap is not None:
            kwargs["mip_gap"] = cfg.mip_rel_gap
        if cfg.time_limit is not None:
            kwargs["time_limit_seconds"] = cfg.time_limit

        # flixopt solver wrappers accept advanced tuning parameters via `extra_options`.
        # Use explicit mappings per solver family for predictable behavior.
        is_gurobi = solver_name == FlixOptSolverName.GUROBI.value
        is_highs = solver_name == FlixOptSolverName.HIGHS.value
        if is_gurobi:
            option_key_map = {
                "threads": "Threads",
                "mip_focus": "MIPFocus",
                "heuristics": "Heuristics",
                "presolve": "Presolve",
                "cuts": "Cuts",
            }
        elif is_highs:
            option_key_map = {
                "threads": "threads",
                "mip_focus": "mip_focus",
                "heuristics": "heuristics",
                "presolve": "presolve",
                "cuts": "cuts",
            }
        else:
            option_key_map = {
                "threads": "threads",
                "mip_focus": "mip_focus",
                "heuristics": "heuristics",
                "presolve": "presolve",
                "cuts": "cuts",
            }
        extra_options: dict[str, Any] = {}
        if cfg.threads is not None:
            extra_options[option_key_map["threads"]] = cfg.threads
        if cfg.mip_focus is not None:
            extra_options[option_key_map["mip_focus"]] = cfg.mip_focus
        if cfg.heuristics is not None:
            extra_options[option_key_map["heuristics"]] = cfg.heuristics
        if cfg.presolve is not None:
            extra_options[option_key_map["presolve"]] = cfg.presolve
        if cfg.cuts is not None:
            extra_options[option_key_map["cuts"]] = cfg.cuts
        if cfg.additional_options is not None:
            extra_options.update(cast(dict[str, Any], cfg.additional_options))
        if extra_options:
            kwargs["extra_options"] = extra_options

        return solver_cls(**kwargs)
