"""
Description: Collection of configuration and data models for the FlixOpt model component.
Authors: Martin Altenburger
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator
import flixopt as fx # type: ignore[import-untyped]

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
    model_config = ConfigDict(
        extra="forbid"
    )
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

class FlixOptBus(BaseModel):
    """
    Model to define a flow in the flixopt model, like it is used in the flixopt library
    https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Bus/

    """
    model_config = ConfigDict(
        extra="forbid"
    )
    label: str = Field(
        ...,
        description="Label of the flow",
    )
    penalty: Optional[float | int] = Field(
        None,
        description="Penalty cost for the flow",
    )

class FlixOptEffect(BaseModel):
    """
    Model to define a single effect in the flixopt model, like it is used in the flixopt library
    https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Effect/

    """
    model_config = ConfigDict(
        extra="forbid"
    )
    label: str = Field(
        ...,
        description="Label of the effect",
    )
    description:str = Field(
        "",
        description="Description of the effect, default is empty string",
    )
    #TODO add units from encodapy units
    unit: str = Field(
        ...,
        description="Unit of the effect",
    )
    objective: bool = Field(
        False,
        description="""
        Whether the effect is part of the objective function, only one effect can be objective
        """,
    )

class FlixOptConverterTypes(Enum):
    """
    Types of FlixOpt converters, supported by encodapy FlixOpt model component
    TODO: describe the converter types and add more types if needed
    """
    BOILER = "boiler"
    POWER2HEAT = "power2heat"
    CHP = "chp"
    SUBSTATION = "substation"
    BIDIRECTIONAL_SUBSTATION = "bidirectional_substation"

class PowerRange(BaseModel):
    """
    Model to define the power range of a converter in the flixopt model in percentages
    """
    model_config = ConfigDict(
        extra="forbid"
    )
    min_power: float | int = Field(
        0,
        description="Minimum power of the converter, default is 0",
    )
    max_power: float | int = Field(
        100,
        description="Maximum power of the converter, default is 100",
    )

class FlixOptStatusParameters(BaseModel):
    """
    Model to define the status parameters of a converter in the flixopt model
    """
    model_config = ConfigDict(
        extra="forbid"
    )
    min_up_time: Optional[float | int] = Field(
        None,
        description="Minimum up time of the converter in hours",
    )
    max_up_time: Optional[float | int] = Field(
        None,
        description="Maximum up time of the converter in hours",
    )
    min_down_time: Optional[float | int] = Field(
        None,
        description="Minimum down time of the converter in hours",
    )
    max_down_time: Optional[float | int] = Field(
        None,
        description="Maximum down time of the converter in hours",
    )
    startup_effects: Optional[dict[str, float | int]] = Field(
        None,
        description="""Startup effects of the converter,
        where the key is the label of the effect 
        and the value is the amount of the effect per startup""",
        #TODO could we check this?
    )


class FlixOptConverter(BaseModel):
    """
    Model to define a converter in the flixopt model, like it is used in the flixopt library
    https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Converter/
    """
    # The model_config is set to forbid extra fields to ensure to use submodels for
    # specific converter types (e.g. FlixOptCHPConverter).
    model_config = ConfigDict(extra="forbid")

    label: str = Field(
        ...,
        description="Label / Name of the converter",
    )
    converter_type: FlixOptConverterTypes = Field(
        ...,
        description="Type of the converter, from the FlixOptConverterTypes enum",
    )

    thermal_efficiency: float | int = Field(
        ...,
        description="Thermal efficiency of the converter [0 ... 1]",
    )
    input_flow: str = Field(
        ...,
        description="Label of the fuel flow to the converter",
    )
    thermal_flow: str = Field(
        ...,
        description="Label of the thermal flow from the converter",
    )
    thermal_nominal_power: float | int = Field(
        ...,
        description="Nominal thermal power of the converter",
    )
    thermal_power_range: PowerRange = Field(
        default=PowerRange.model_validate({}),
        description="Thermal power range of the boiler converter in percentages",
    )
    status_parameters: FlixOptStatusParameters = Field(
        default = FlixOptStatusParameters.model_validate({}),
        description= """
        Optional status parameters for the converter which includes information 
        about startup and shutdown limitations"""
    ) # TODO: add more converter types and their specific parameters / startup costs etc.
    previous_power: Optional[float | int | str] = Field(
        None,
        description="""Previous power of the converter in kW
        or as label of an input value, used to define the previous flow rate""",
    )
    operation_time: Optional[float | int | str] = Field(
        None,
        description="""Operation time of the converter in hours
        or as label of an input value, used to define the operation time for startup costs"""
    )

class FlixOptCHPConverter(FlixOptConverter):
    """
    Model to define a CHP converter in the flixopt model, 
    which inherits from the FlixOptConverter model
    and adds specific parameters for the CHP converter type
    
    Keep in mind, the `nominal_power` parameter in the FlixOptConverter model is the 
    nominal thermal power of the CHP converter, while the nominal electrical power can be 
    calculated from the thermal efficiency and the electrical efficiency of the CHP converter.
    """
    model_config = ConfigDict(
        extra="forbid"
    )
    electrical_efficiency: float | int = Field(
        ...,
        description="Electrical efficiency of the CHP converter",
    )
    electrical_flow: str = Field(
        ...,
        description="Label of the electrical flow for the CHP converter",
    )


class FlixOptStorage(BaseModel):
    """
    Model to define a storage in the flixopt model, like it is used in the flixopt library
    https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Storage/
    """
    model_config = ConfigDict(
        extra="forbid"
    )
    label: str
    bus: str = Field(
        ...,
        description="Label of the flow for the storage",
    )
    nominal_power: float | int = Field(
        ...,
        description="Nominal power of the storage in kW",
    )
    nominal_capacity: float | int | str = Field(
        ...,
        description="""Nominal capacity of the storage in kWh
        or as label of an input value, which is then used to read the nominal capacity""",
    )
    relative_self_discharge: Optional[float | int] = Field(
        0.0,
        description="Relative self-discharge of the storage in percentage per hour",
    )
    eta_charge: Optional[float | int] = Field(
        100.0,
        description="Charging efficiency of the storage in percentage",
    )
    eta_discharge: Optional[float | int] = Field(
        100.0,
        description="Discharging efficiency of the storage in percentage",
    )
    start_soc: float | int | str = Field(
        0,
        description="""
        Starting state of charge (SOC) of the storage at the beginning of the optimization period,
        can be defined as a percentage of the nominal capacity (e.g. 50) or as an label
        of a input value (e.g. `initial_soc`) which is then used to read the starting SOC 
        from the input data and is required there in Percentage of the nominal capacity as well
        """,
    )
    minimal_soc: float | int = Field(
        0,
        description="""
        Minimal state of charge (SOC) of the storage in percentage of the nominal capacity""",
    )
    maximal_soc: float | int = Field(
        100,
        description="""
        Maximal state of charge (SOC) of the storage in percentage of the nominal capacity""",
    )

class EnergyDirection(Enum):
    """
    Enum to define the energy direction for a sink or source in the flixopt model
    """
    SINK = "sink"
    SOURCE = "source"
    BIDIRECTIONAL = "bidirectional"

class FlixOptSinkSource(BaseModel):
    """
    Model to define a sink or source in the flixopt model, like it is used in the flixopt library
    https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Element/
    """
    model_config = ConfigDict(
        extra="forbid"
    )
    label: str = Field(
        ...,
        description="Label of the sink/source",
    )
    direction: EnergyDirection = Field(
        ...,
        description="Direction of the energy flow, either 'sink', 'source' or 'bidirectional'",
    )
    nominal_power: Optional[float | int] = Field(
        None,
        description="Nominal power of the sink/source in kW, only required for sources",
    )
    input_bus: Optional[str] = Field(
        None,
        description="Label of the flow for the sink, for the source with an input flow",
    )
    input_label: Optional[str] = Field(
        None,
        description="""
        Label of the input time series for the sink (heat demand ...), 
        if the sink has a time series input""",
    )
    input_effects: Optional[dict[str, float | int]] = Field(
        None,
        description="""
        Optional dictionary to define the effect of the sink
        on the defined effects in the model, where the key is the label of the effect
        and the value is the amount of the effect per kWh of energy flow

        Only used, if input_label is None and the input bus is defined.

        Example::

            {
                "costs": 0.15
            }

        """,
    )
    output_bus: Optional[str] = Field(
        None,
        description="""
        Label of the output flow for the source, only required for source with an output flow
        """,
    )
    output_label: Optional[str] = Field(
        None,
        description="""
        Label of the output time series for the source, if the source has a time series output""",
    )
    output_effects: Optional[dict[str, float | int]] = Field(
        None,
        description="""
        Optional dictionary to define the effect of the source
        on the defined effects in the model, where the key is the label of the effect
        and the value is the amount of the effect per kWh of energy flow

        Only used, if output_label is None and the output bus is defined.

        Example::

            {
                "costs": 0.15
            }

        """,
    )

    @model_validator(mode='after')
    def _check_the_required_fields(self):
        """
        Validator to check, if the required fields for the sink/source are defined
        depending on the direction and the other fields

        Raises:
            ValueError: If the required fields are not defined
        """
        if self.direction == EnergyDirection.SINK:
            if self.input_bus is None:
                raise ValueError("For a sink, input_bus must be defined")

        elif self.direction == EnergyDirection.SOURCE:
            if self.output_bus is None:
                raise ValueError("For a source, output_bus must be defined")
        elif self.direction == EnergyDirection.BIDIRECTIONAL:
            if self.input_bus is None and self.output_bus is None:
                raise ValueError("For a bidirectional sink/source, "
                                 "input_bus and output_bus (optional) must be defined")
            if self.output_bus is None:
                self.output_bus = self.input_bus
            if self.nominal_power is None:
                raise ValueError("For a bidirectional sink/source, nominal_power must be defined")
        return self


class FlixOptModel(BaseModel):
    """
    Model to hold the flixopt Model used in the component

    # Specific constraints
    To add constraints to the FlixOpt model, a Python file or module can be defined in the
    'constraints_function' field. This needs to include a function called 
    'add_constraints(optimization: fx.Optimization, config: FlixOptModel)' 
    that adds additional constraints to the FlixOpt optimization model.
    This function is then called in the component after the FlixOpt model has been built.
    You can add more subfunctions to this function to add constraints.
    """
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

    buses: list[FlixOptBus] = Field(
        ...,
        description="""
        List of buses in in the model, which are required to build the flixopt model
        (https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Bus/)
        """,
    )
    effects: list[FlixOptEffect] = Field(
        ...,
        description="""
        List of effects in in the model, which are required to build the flixopt optimization model 
        (https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Effect/)
        """,
    )
    converters: list[FlixOptConverter | FlixOptCHPConverter] = Field(
        ...,
        description="""
        List of converters in in the model, which are required to build the flixopt model
        (https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Converter/)
        """,
    )
    exchangers: list[FlixOptSinkSource] = Field(
        ...,
        description="""
        List of sinks and sources in in the model, which are required to build the flixopt model
        """,
    )
    storages: list[FlixOptStorage] = Field(
        ...,
        description="""
        List of storages in in the model, which are required to build the flixopt model 
        (https://flixopt.github.io/flixopt/latest/user-guide/mathematical-notation/elements/Storage/)
        """,
    )
    constraints_function: Optional[str] = Field(
        None,
        description="""
        Path to a python file or python module which includes a function `add_constraints`
        used to add additional constraints to the flixopt optimization model
        """,
    )
