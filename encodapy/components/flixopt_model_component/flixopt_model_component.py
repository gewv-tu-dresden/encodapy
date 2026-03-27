"""
Defines the FlixOptModelComponent class to perform optimizations using the FlixOpt library.
"""
# pylint: disable=no-member
from typing import Optional, Union, Any, Literal, overload
from collections.abc import Callable
from datetime import timezone, datetime
import importlib.util
import importlib
import inspect
from pathlib import Path
from pydantic import ValidationError
import pandas as pd
import numpy as np
import xarray
import flixopt as fx # type: ignore[import-untyped]
from loguru import logger
from encodapy.components.basic_component import BasicComponent
from encodapy.utils.datapoints import DataPointTimeSeries
from encodapy.components.flixopt_model_component.flixopt_models import (
    FlixOptModel,
    FLIXOPT_CONFIG_MAP,
    FlixOptConverterTypes,
    FlixOptConverter,
    FlixOptCHPConverter,
    EnergyDirection,
    FlixOptSinkSource
)

from encodapy.components.flixopt_model_component.flixopt_model_component_config import (
    FlixoptModelComponentInputData,
    FlixoptModelComponentOutputData,
    FlixoptModelComponentConfigData,
    DataPointFlixoptModelConfig
)


class FlixoptModelComponent(BasicComponent):
    """
    Class for a FlixOpt component based on a model defined for the FlixOpt library.
    """

    def __init__(
        self,
        config,
        component_id: str,
        static_data=None,
    ) -> None:
        # BasicComponent.__init__ calls prepare_component(), so this must exist beforehand.
        self.constraint_function: Optional[Callable] = None

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )
        self.config_data: FlixoptModelComponentConfigData
        self.input_data: FlixoptModelComponentInputData
        self.output_data: FlixoptModelComponentOutputData

        # Component-specific initialization logic
        self.flixopt_model: FlixOptModel
        self.df_input: Optional[pd.DataFrame] = None
        self.df_input_timezone: Optional[timezone] = None
        self._bidirectional_substation_pairs: list[
            tuple[fx.components.LinearConverter, fx.components.LinearConverter, float, float]
        ] = []
        self._bidirectional_substation_labels: dict[str, tuple[str, str]] = {}

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        # Example: Initialize FlixOpt model or other resources here

        # Set flixopt log level based on configuration
        FLIXOPT_CONFIG_MAP[self.config_data.log_level.value]()

        try:
            if not isinstance(self.config_data.flixopt_model, DataPointFlixoptModelConfig):
                raise ValueError("flixopt_model must be of type DataPointFlixoptModelConfig.")
            if isinstance(self.config_data.flixopt_model.value, dict):
                self.flixopt_model = FlixOptModel.model_validate(
                    self.config_data.flixopt_model.value
                )
            elif isinstance(self.config_data.flixopt_model.value, str):
                with open(self.config_data.flixopt_model.value, "r", encoding="utf-8") as file:
                    model_config_json = file.read()
                self.flixopt_model = FlixOptModel.model_validate_json(model_config_json)
            else:
                # should not happen due to validation, but just in case
                raise ValueError(
                    "flixopt_model must be a dict or a path to a json file."
                )
        except (ValidationError, FileNotFoundError) as e:
            logger.error(f"Error loading flixopt model configuration: {e}")
            raise e
        if self.flixopt_model.constraints_function is not None:
            func = self._load_helper_functions(
                path = self.flixopt_model.constraints_function,
                symbol = "add_constraints")
            self.constraint_function = func

    def _load_helper_functions(self,
                               path: str,
                               symbol: str
                               ) -> Optional[Callable]:
        """
        Load custom constraint functions from either a file path or python module reference.

        """
        module: Any
        module_ref = path.strip()

        is_file_reference = module_ref.endswith(".py") or Path(module_ref).suffix == ".py"
        if is_file_reference:
            constraints_path = Path(module_ref).resolve()
            spec = importlib.util.spec_from_file_location(constraints_path.stem, constraints_path)
            if spec is None:
                raise ImportError(
                    f"Could not create module spec for constraints file: {constraints_path}"
                )
            loader = spec.loader
            if loader is None:
                raise ImportError(f"No loader available for constraints file: {constraints_path}")
            module = importlib.util.module_from_spec(spec)
            loader.exec_module(module)
        else:
            module = importlib.import_module(module_ref)

        if symbol:
            function = getattr(module, symbol, None)
            if function is None or not inspect.isfunction(function):
                raise ImportError(
                    f"Constraint function '{symbol}' not found in '{module_ref}'."
                )
            return function

        return None

    def _get_input_arrays(self,
                          column:str) -> np.ndarray:
        """
        Get a timeseries as np.ndarry from the input files

        Args:
            column (str): Label of the input time series to retrieve

        Raises:
            ValueError: If the input DataFrame is not prepared
            ValueError: If the specified column is not found in the input DataFrame

        Returns:
            np.ndarray: The time series data as a NumPy array
        """
        if self.df_input is None:
            logger.error("Input DataFrame is not prepared.")
            raise ValueError("Input DataFrame is not prepared.")

        if column not in self.df_input.columns:
            logger.error(f"Column {column} not found in input DataFrame.")
            raise ValueError(f"Column {column} not found in input DataFrame.")

        return self.df_input[column].to_numpy()
    # Marker for typ checker
    @overload
    def _get_input_value(self,
                         label: str,
                         none_allowed: Literal[False] = False
                         ) -> float | int:
        ...

    @overload
    def _get_input_value(self,
                         label: str,
                         none_allowed: Literal[True] = True
                         ) -> float | int | None:
        ...

    def _get_input_value(self,
                         label: str,
                         none_allowed: bool = False
                         ) -> float | int | None:
        """
        Get a single input value from the input data based on the label
        Args:
            label (str): Label of the input value to retrieve
            none_allowed (bool): Whether None is an allowed value for the input, defaults to False
        Returns:
            float | int | None: The value of the input if found, otherwise None
        Raises:
            ValueError: If the input data is not prepared, the label is not found, \
                or the value is not a float or int
        """
        if self.input_data is None:
            logger.error("Input data is not prepared.")
            raise ValueError("Input data is not prepared.")

        # Convert input data to a dictionary for easier access, because the input attributes
        # are defined dynamically based on the model definition
        # and we can not be sure about the attribute names here
        input_data = self.input_data.model_dump()
        if label not in list(input_data.keys()):
            error_message = f"Label {label} not found in input data of the flixopt component."
            logger.error(error_message)
            raise ValueError(error_message)

        value = input_data[label].get("value")

        if none_allowed:
            if value is None or isinstance(value, (float, int)):
                return value
            logger.error(f"Input value for label {label} is neither float/int nor None.")
            raise ValueError(
                f"Input value for label {label} is neither float/int nor None."
            )

        if not isinstance(value, (float, int)):
            logger.error(f"Input value for label {label} is not a float or int.")
            raise ValueError(f"Input value for label {label} is not a float or int.")

        return value

    def prepare_input_data(self) -> None:
        """
        Prepare the input data for the FlixOpt component
        - Merge input time series into a single DataFrame
        - Ensure proper datetime index and frequency
        - Remove timezone information

        """
        df_input = pd.DataFrame()

        for input_key, input_value in self.input_data:
            logger.debug(f"Processing input {input_key} with value type {type(input_value)}")

            try:
                input_value_validated = DataPointTimeSeries.model_validate(input_value)
            except ValidationError:
                # Validation could fail if the input value is not a time series,
                # which is expected for some inputs
                continue
            if isinstance(input_value_validated.value, pd.Series):
                df_input = df_input.join(
                    input_value_validated.value.rename(input_key).to_frame(), how='outer')

        if not isinstance(df_input.index, pd.DatetimeIndex):
            logger.error("Input time series must have a DatetimeIndex, "
                         "can not update input dataframes.")
            # should not happen due to validation
            return
        freq: Optional[Union[str, pd.offsets.BaseOffset]] = \
            df_input.index.freq

        if freq is None:
            freq = pd.infer_freq(df_input.index)
        if freq is None:
            freq = pd.offsets.Hour(1)
            logger.warning("Could not infer frequency of input time series. Defaulting to 1H.")
        # Save timezone information to add it back later
        self.df_input_timezone = df_input.index.tz if isinstance(df_input.index.tz, timezone) \
            else None
        df_input.index = pd.DatetimeIndex(df_input.index.tz_localize(None), freq=freq)

        self.df_input = df_input

    def _prepare_flixopt_flow_system(self
                                     ) -> fx.FlowSystem:
        """
        Prepare the FlixOpt model for the optimization
        Adds buses, effects and components based on the model definition

        Returns:
            fx.FlowSystem: Configured FlowSystem for optimization
        """
        try:
            assert self.df_input is not None, "Input data preparation failed."
            assert isinstance(self.df_input.index, pd.DatetimeIndex), \
                "Input time series must have a DatetimeIndex"
        except AssertionError as e:
            logger.error(f"Error in input data: {e}")
            raise ValueError from e
        flow_system = fx.FlowSystem(self.df_input.index)

        for bus in self.flixopt_model.buses:
            flow_system.add_elements(
                fx.Bus(
                    bus.label,
                    excess_penalty_per_flow_hour=bus.penalty
                )
            )
        for effect in self.flixopt_model.effects:
            flow_system.add_elements(
                fx.Effect(
                    label=effect.label,
                    unit=effect.unit,
                    description=effect.description,
                    is_objective=effect.objective
                )
            )
        logger.debug(
            f"Prepared FlowSystem with {len(flow_system.buses)} buses "
            f"and {len(flow_system.effects)} effects."
        )

        return flow_system

    def _add_output_flow_to_converter(self,
                                      converter:FlixOptConverter
                                      )-> fx.Flow:
        """Add the output flow to a converter based on the model definition of the converter
        Args:
            converter (FlixOptConverter): Converter for which to add the output flow
        Returns:
            fx.Flow: The output flow for the converter
        """
        if isinstance(converter.previous_power, str):
            previous_flow_rate = self._get_input_value(
                label=converter.previous_power,
                none_allowed=True
            )
        else:
            previous_flow_rate = converter.previous_power

        return fx.Flow(
            label=converter.thermal_flow,
            bus=converter.thermal_flow,
            size=converter.thermal_nominal_power,
            relative_minimum=converter.thermal_power_range.min_power/100,
            relative_maximum=converter.thermal_power_range.max_power/100,
            previous_flow_rate=previous_flow_rate
        )

    def _add_input_flow_to_converter(self,
                                     converter:FlixOptConverter
                                     ) -> fx.Flow:
        return fx.Flow(
            label=converter.input_flow,
            bus=converter.input_flow,
            size=converter.thermal_nominal_power / converter.thermal_efficiency,
        )

    def _add_status_parameters_to_converter(self,
                                            converter:FlixOptConverter
                                            ) -> fx.StatusParameters:
        """
        Function to set the status parameters,
        adjusts the minimum uptime based on the operation time of the converter
        to reduce the remaining minimum uptime at the optimization start.
        Args:
            converter (FlixOptConverter): Converter for which to set the status parameters
        Returns:
            fx.StatusParameters: The status parameters for the converter
        """
        # Use operation_time to reduce the remaining minimum uptime at the optimization start.
        if isinstance(converter.operation_time, str):
            operation_time = self._get_input_value(
                label=converter.operation_time,
                none_allowed=True
            )
        elif isinstance(converter.operation_time, (float, int)):
            operation_time = converter.operation_time
        else:
            operation_time = None

        df_input = self.df_input
        min_uptime_value: float | int | np.ndarray | None
        if (
            operation_time is not None
            and converter.status_parameters.min_up_time is not None
            and df_input is not None
            and isinstance(df_input.index, pd.DatetimeIndex)
        ):
            full_min_uptime = float(converter.status_parameters.min_up_time)
            elapsed_hours = (df_input.index - df_input.index[0]).total_seconds() / 3600
            remaining_profile = full_min_uptime - float(operation_time) - elapsed_hours
            min_uptime_profile = np.full(len(df_input.index), full_min_uptime, dtype=float)

            # Reduce only during the initial carry-over runtime window.
            # As soon as 0 would be reached, switch back to the normal min_uptime.
            reset_indices = np.where(remaining_profile <= 0)[0]
            reset_idx = int(reset_indices[0]) if len(reset_indices) > 0 else len(min_uptime_profile)
            if reset_idx > 0:
                min_uptime_profile[:reset_idx] = np.maximum(remaining_profile[:reset_idx], 0.0)

            min_uptime_value = min_uptime_profile
        else:
            min_uptime_value = converter.status_parameters.min_up_time

        return fx.StatusParameters(
            min_uptime=min_uptime_value,
            max_uptime=converter.status_parameters.max_up_time,
            min_downtime=converter.status_parameters.min_down_time,
            max_downtime=converter.status_parameters.max_down_time,
            effects_per_startup=converter.status_parameters.startup_effects
        )

    def _add_boiler_converter(self,
                              converter:FlixOptConverter
                              )  -> fx.linear_converters.Boiler:
        """
        Prepare a Boiler converter based on the FlixOptConverter model
        Args:
            converter (FlixOptConverter): Converter model to define the boiler
        Returns:
            fx.linear_converters.Boiler: FlixOpt Component for the boiler converter
        """

        return fx.linear_converters.Boiler(
            label=converter.label,
            thermal_efficiency=converter.thermal_efficiency,
            status_parameters=self._add_status_parameters_to_converter(converter),
            thermal_flow=self._add_output_flow_to_converter(converter),
            fuel_flow= self._add_input_flow_to_converter(converter),
        )
    def _add_p2h_converter(self,
                          converter:FlixOptConverter
                          ) -> fx.linear_converters.Power2Heat:
        """
        Prepare a Power2Heat converter based on the FlixOptConverter model
        Args:
            converter (FlixOptConverter): Converter model to define the Power2Heat converter
        Returns:
            fx.linear_converters.Power2Heat: FlixOpt Component for the Power2Heat converter
        """
        return fx.linear_converters.Power2Heat(
            label = converter.label,
            thermal_efficiency=converter.thermal_efficiency,
            status_parameters=self._add_status_parameters_to_converter(converter),
            thermal_flow=self._add_output_flow_to_converter(converter),
            electrical_flow=self._add_input_flow_to_converter(converter)
        )
    def _add_chp_converter(self,
                           converter:FlixOptCHPConverter
                           ) -> fx.linear_converters.CHP:
        """
        Prepare a CHP converter based on the FlixOptCHPConverter model
        Uses the same structure like the boiler and power2heat converter,
        but adds the electrical flow and efficiency
        Args:
            converter (FlixOptCHPConverter): Converter model to define the CHP converter
        Returns:
            fx.linear_converters.CHP: FlixOpt Component for the CHP converter
        """
        if not isinstance(converter, FlixOptCHPConverter):
            raise ValueError("Converter must be of type FlixOptCHPConverter to be added as CHP.")
        return fx.linear_converters.CHP(
            label=converter.label,
            thermal_efficiency=converter.thermal_efficiency,
            electrical_efficiency=converter.electrical_efficiency,
            status_parameters=self._add_status_parameters_to_converter(converter),
            thermal_flow=self._add_output_flow_to_converter(converter),
            electrical_flow=fx.Flow(
                label=converter.electrical_flow,
                bus=converter.electrical_flow,
                size=converter.thermal_nominal_power / converter.thermal_efficiency \
                    * converter.electrical_efficiency,
                ),
            fuel_flow=self._add_input_flow_to_converter(converter)
        )

    def _add_substation_converter(self,
                                  converter:FlixOptConverter
                                  )-> fx.linear_converters.LinearConverter:
        """
        Prepare a Substation converter based on the FlixOptConverter model
        Args:
            converter (FlixOptConverter): Converter model to define the Substation converter
        Returns:
            fx.linear_converters.LinearConverter: FlixOpt Component for the Substation converter
        """

        return fx.components.LinearConverter(
            label=converter.label,
            inputs=[self._add_input_flow_to_converter(converter)],
            outputs=[self._add_output_flow_to_converter(converter)],
            conversion_factors=[
                { converter.input_flow: 1, converter.thermal_flow: converter.thermal_efficiency }
            ],
            status_parameters=self._add_status_parameters_to_converter(converter)
        )


    def _add_bidirectional_substation_converter(self,
                                                converter: FlixOptConverter
                                                ) -> list[fx.components.LinearConverter]:
        """
        Build a bidirectional substation converter with one forward and one reverse component.
        Simultaneous operation in both directions is prevented later via binary constraints.
        """
        efficiency = float(converter.thermal_efficiency)
        if efficiency <= 0:
            raise ValueError(
                f"Converter {converter.label} has invalid thermal_efficiency {efficiency}."
            )

        forward = fx.components.LinearConverter(
            label=f"{converter.label}_fwd",
            inputs=[self._add_input_flow_to_converter(converter)
            ],
            outputs=[self._add_output_flow_to_converter(converter)],
            conversion_factors=[
                { converter.input_flow: 1, converter.thermal_flow: efficiency }
            ],
            status_parameters=self._add_status_parameters_to_converter(converter)
        )

        reverse = fx.components.LinearConverter(
            label=f"{converter.label}_rev",
            inputs=[self._add_output_flow_to_converter(converter)],
            outputs=[self._add_input_flow_to_converter(converter)],
            conversion_factors=[
                { converter.thermal_flow: 1, converter.input_flow: efficiency }
            ],
            status_parameters=self._add_status_parameters_to_converter(converter)
        )

        self._bidirectional_substation_pairs.append(
            (
                forward,
                reverse,
                float(converter.thermal_nominal_power / efficiency),
                float(converter.thermal_nominal_power),
            )
        )
        self._bidirectional_substation_labels[converter.label] = (forward.label, reverse.label)
        return [forward, reverse]

    def _get_converters(self) -> list[fx.components.LinearConverter]:
        """
        Prepare the FlixOpt components based on the model definition

        Returns:
            list[fx.components.LinearConverter]: List of FlixOpt converters for the optimization
        """
        self._bidirectional_substation_pairs = []
        self._bidirectional_substation_labels = {}
        converters: list[fx.components.LinearConverter] = []

        for converter in self.flixopt_model.converters:

            match converter.converter_type:
                case FlixOptConverterTypes.BOILER:

                    converters.append(
                        self._add_boiler_converter(converter)
                    )
                case FlixOptConverterTypes.POWER2HEAT:
                    converters.append(
                        self._add_p2h_converter(converter)
                    )
                case FlixOptConverterTypes.CHP:
                    if not isinstance(converter, FlixOptCHPConverter):
                        logger.error(
                            f"Converter {converter.label} is defined as CHP, "
                            f"but does not have the required attributes for a CHP converter.")
                        continue
                    converters.append(
                        self._add_chp_converter(converter)
                    )
                case FlixOptConverterTypes.SUBSTATION:
                    converters.append(
                        self._add_substation_converter(converter)
                    )
                case FlixOptConverterTypes.BIDIRECTIONAL_SUBSTATION:
                    converters.extend(
                        self._add_bidirectional_substation_converter(converter)
                    )
                case _:
                    logger.warning(
                        f"Converter type {converter.converter_type} not supported yet."
                    )

        return converters

    def _get_storages(self,
                      storage_config = None) -> list[fx.Storage]:
        """
        Prepare the FlixOpt storage components based on the model definition

        Returns:
            list[fx.Component]: List of FlixOpt storage components for the optimization

        TODO: 
            - should we set a final capacity? --> same like the start soc
            - soc as percentage or absolute value? currently percentage
            - do we need different bus for charging and discharging? \
                currently the same, but with different flow labels
        """
        storages = []
        storage_config = self.flixopt_model.storages if storage_config is None else storage_config

        for storage in storage_config:
            if isinstance(storage.nominal_capacity, str):
                nominal_capacity = self._get_input_value(storage.nominal_capacity)
            elif isinstance(storage.nominal_capacity, (float, int)):
                nominal_capacity = storage.nominal_capacity
            else:
                raise ValueError("Nominal capacity must be a float, int "
                                 "or a string referring to an input value.")
            if isinstance(storage.start_soc, str):
                initial_soc = self._get_input_value(storage.start_soc) / 100 \
                    * nominal_capacity
            elif isinstance(storage.start_soc, (float, int)):
                initial_soc = storage.start_soc / 100 * nominal_capacity
            # should not happen due to validation, but just in case
            else:
                initial_soc = 0

            # inital soc needs to be within the capacity of the storage
            initial_soc = max(storage.minimal_soc / 100 * nominal_capacity,
                              min(initial_soc, storage.maximal_soc / 100 * nominal_capacity))

            storages.append(
                fx.Storage(
                    label=storage.label,
                    charging=fx.Flow(
                        label=storage.bus + "_charge",
                        bus=storage.bus,
                        size=storage.nominal_power,
                    ),
                    discharging=fx.Flow(
                        label=storage.bus + "_discharge",
                        bus=storage.bus,
                        size=storage.nominal_power,
                    ),
                    capacity_in_flow_hours=nominal_capacity,
                    eta_charge=storage.eta_charge / 100 if storage.eta_charge is not None else None,
                    eta_discharge=storage.eta_discharge / 100 if storage.eta_discharge is not None \
                        else None,
                    relative_loss_per_hour=storage.relative_self_discharge / 100 \
                        if storage.relative_self_discharge is not None else None,
                    prevent_simultaneous_charge_and_discharge=True,
                    initial_charge_state=initial_soc,
                    relative_minimum_charge_state=storage.minimal_soc / 100,
                    relative_maximum_charge_state=storage.maximal_soc / 100,
                    minimal_final_charge_state = initial_soc
                )
            )
        return storages

    def _get_flow_effects(self,
                          sink_source: FlixOptSinkSource,
                          direction: EnergyDirection) -> dict:
        """Get the flow effects for a sink/source based on the model definition and direction
        Args:
            sink_source (FlixOptSinkSource): The sink/source for which to get the flow effects
            direction (EnergyDirection): The direction of the flow (sink or source)
        Returns:
            dict: A dictionary containing the flow effects for the sink/source and direction
        """
        match direction:
            case EnergyDirection.SINK:
                check_label = sink_source.input_label
            case EnergyDirection.SOURCE:
                check_label = sink_source.output_label
            case _:
                logger.error(f"Energy direction {direction} not supported for flow effects.")
                return {}

        flow_effects: dict["str", Any] = {}
        match check_label:
            case None:
                flow_effects["effects_per_flow_hour"] = sink_source.input_effects \
                    if direction == EnergyDirection.SINK else sink_source.output_effects
            case _:
                flow_effects["fixed_relative_profile"] = self._get_input_arrays(check_label)
                flow_effects["size"] = 1

        return flow_effects

    def _get_flow_information(self,
                              sink_source: FlixOptSinkSource,
                              direction: EnergyDirection
                              ) -> dict:
        """Get the flow information for a sink/source based on the model definition and direction
        Args:
            sink_source (FlixOptSinkSource): The sink/source for which to get the flow information
            direction (EnergyDirection): The direction of the flow (sink or source)
        Returns:
            dict: A dictionary containing the flow information for the sink/source and direction
        """
        flow_information:dict = {
                "size": sink_source.nominal_power,
            }
        match direction:
            case EnergyDirection.SINK:
                flow_information["bus"] = sink_source.input_bus
                flow_information["label"] = f"{sink_source.input_bus}_in"
                # needs a unique label, also for SinkAndSource
                flow_information.update(self._get_flow_effects(sink_source, direction))
            case EnergyDirection.SOURCE:
                flow_information["bus"] = sink_source.output_bus
                flow_information["label"] = f"{sink_source.output_bus}_out"
                flow_information.update(self._get_flow_effects(sink_source, direction))
            case _:
                logger.error(f"Energy direction {direction} not supported for flow information.")

        return flow_information


    def _get_sinks_and_sources(self) -> list[Union[fx.Sink, fx.Source]]:
        """
        Prepare the FlixOpt sink and source components based on the model definition

        Returns:
            list[Union[fx.Sink, fx.Source]]: List of FlixOpt sink and source components \
                for the optimization
        """

        sinks_and_sources: list[Union[fx.Sink, fx.Source]] = []

        for sink_source in self.flixopt_model.exchangers:

            match sink_source.direction:
                case EnergyDirection.SINK:
                    sinks_and_sources.append(
                        fx.Sink(
                            label=sink_source.label,
                            inputs=[
                                fx.Flow(
                                    **self._get_flow_information(sink_source, sink_source.direction)
                                )
                            ]
                        )
                    )
                case EnergyDirection.SOURCE:
                    sinks_and_sources.append(
                        fx.Source(
                            label=sink_source.label,
                            outputs=[
                                fx.Flow(
                                    **self._get_flow_information(sink_source, sink_source.direction)
                                )
                            ]
                        )
                    )
                case EnergyDirection.BIDIRECTIONAL:
                    sinks_and_sources.append(
                        fx.SourceAndSink(
                            label=sink_source.label,
                            outputs=[
                                fx.Flow(
                                    **self._get_flow_information(sink_source,
                                                                 EnergyDirection.SOURCE)
                                )],
                            inputs=[
                                fx.Flow(
                                    **self._get_flow_information(sink_source,EnergyDirection.SINK)
                                )
                            ],
                            prevent_simultaneous_flow_rates=True
                        )
                    )
                case _:
                    logger.warning(
                        f"Energy direction {sink_source.direction} not supported yet."
                    )
        return sinks_and_sources

    def _add_bidirectional_substation_constraints(
        self,
        optimization: fx.Optimization,
    ) -> None:
        """
        Prevent simultaneous forward and reverse operation for bidirectional substations.
        """
        base_coords = optimization.model.get_coords()
        if base_coords is None:
            raise ValueError("Optimization model coordinates are not available.")

        for idx, (forward, reverse, max_forward, max_reverse) in enumerate(
            self._bidirectional_substation_pairs
        ):
            z_direction = optimization.model.add_variables(
                name=f"z_bidir_converter_{idx}",
                coords=base_coords,
                binary=True,
            )

            optimization.model.add_constraints(
                forward.inputs[0].submodel.flow_rate <= z_direction * max_forward,
                name=f"bidir_forward_gate_{idx}",
            )
            optimization.model.add_constraints(
                reverse.inputs[0].submodel.flow_rate <= (1 - z_direction) * max_reverse,
                name=f"bidir_reverse_gate_{idx}",
            )

    def run_optimization(self
                         ) -> Optional[fx.results.Results]:
        """
        Perform the calculations with the FlixOpt library
            The model is built up in this function based on the input data \
                and the model structure defined here.

        Returns:
            fx.results.Results: Results from FlixOpt optimization        
        """
        # Define Flow System and Effects
        flow_system = self._prepare_flixopt_flow_system()

        # Define Converters
        converters = self._get_converters()

        # Define Storage Component
        storages = self._get_storages()
        # flow_system, storages = self._define_stratified_storage_tank(flow_system)

        # Define Sinks and Sources
        sinks_and_sources = self._get_sinks_and_sources()

        # Select components to be included in the flow system
        for element in converters + sinks_and_sources + storages:
            flow_system.add_elements(element)
        # TODO maybe add manually components?


        # Solve Problem
        try:
            optimization = fx.Optimization('encodapy', flow_system)
            optimization.do_modeling()

            # self._add_storage_constraints(optimization, storages)
            self._add_bidirectional_substation_constraints(optimization)

            if self.constraint_function is not None:
                self.constraint_function(optimization)

            optimization.solve(self.config_data.get_solver(), log_main_results=False)
        except Exception as e: #TODO
            logger.error(f"Error during optimization: {e}")
            logger.info(type(e).__name__)
            return None
        logger.debug("Optimization completed with a "
                     f"duration for modeling {optimization.durations.get('modeling', '-')} s "
                     f"and solving {optimization.durations.get('solving', '-')} s. "
                     "The main objective result is "
                     f"{optimization.results.summary.get('Main Results').get('Objective')}.")

        return optimization.results

    def export_results_as_timeseries(self,
                                     results:xarray.core.dataset.Dataset
                                     ) -> pd.DataFrame:
        """
        Export the results of the FlixOpt optimization
        
        Args:
            results (xarray.core.dataset.Dataset): Results from FlixOpt optimization
            
        Returns:
            pd.DataFrame: DataFrame containing all timeseries results
        """
        results_dict: dict[str, Union[pd.DataFrame, pd.Series, np.ndarray]] = {}
        if self.df_input is None or not isinstance(self.df_input.index, pd.DatetimeIndex):
            # That should not happen, but just in case
            error_message = "Input data is not prepared, can not export results as timeseries."
            logger.error(error_message)
            raise ValueError(error_message)

        for var_name in results.data_vars:
            # Convert xarray DataArray to pandas Series/DataFrame
            var_name = str(var_name)
            data_array = results[var_name]

            if 'time' in data_array.dims:
                # Convert Timeseries to pandas Series/DataFrame
                df = data_array.to_dataframe()
                results_dict[var_name] = df
            else:
                # Scalar values
                value = data_array.values
                results_dict[var_name] = value

        # Combine all timeseries into a single DataFrame (optional)
        all_timeseries = pd.DataFrame()
        for var_name, data in results_dict.items():
            if isinstance(data, (pd.DataFrame, pd.Series)):
                if isinstance(data, pd.DataFrame):
                    data = data.reset_index(drop=False)
                all_timeseries[var_name] = data if isinstance(data, pd.Series) else data.iloc[:, -1]
        all_timeseries["time"] = pd.date_range(
            start=self.df_input.index[0],
            periods=len(all_timeseries),
            freq=self.df_input.index.freq,
            tz=self.df_input_timezone)
        all_timeseries.set_index("time", inplace=True)
        # drop last row, because it is often incomplete due to the way the optimization works
        all_timeseries.drop(index=all_timeseries.index[-1], inplace=True)
        # all_timeseries.to_csv(
        #     f"./results/optimization_results_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        #     sep=";", decimal=",", encoding="utf-8") #TODO remove
        return all_timeseries

    def prepare_output_data(self,
                            results:fx.results.Results) -> None:
        """
        Prepare the output data for the FlixOpt component, mapping results to output model

        This function provides the output as FlixoptModelComponentOutputData, 
        with the following variables:
        - Storage levels for all storages in the model like this: `{storage_label}_soc`
        - For all converters in the model, the thermal power like this: \
            `{converter_label}_thermal_power`
        - For all CHP converters in the model, the electrical power like this: \
            `{converter_label}_electrical_power`
        - For all Sink and Sources in the model, the input and output flow rates like this: \
            `{sink_source.label} + "_input"` and `{sink_source.label} + "_output"`

        Args:
            all_timeseries (pd.DataFrame): DataFrame containing all timeseries

        TODO: 
            - Do we need more? maybe add also the input power of converters
            - Do we need a configuration?

        """
        all_timeseries = self.export_results_as_timeseries(results.solution)

        # print(all_timeseries.columns)
        # print(all_timeseries)
        outputs: dict[str, DataPointTimeSeries]= {}
        for storage in self.flixopt_model.storages:
            outputs[storage.label + "_soc"] = DataPointTimeSeries(
                value = all_timeseries.loc[:, f"{storage.label}|charge_state"
                                           ].rename(storage.label + "_soc"))

        for converter in self.flixopt_model.converters:
            output_name = converter.label + "_thermal_power"
            if converter.label in self._bidirectional_substation_labels:
                forward_label, reverse_label = self._bidirectional_substation_labels[converter.label]
                forward_col = f"{forward_label}({converter.thermal_flow})|flow_rate"
                reverse_col = f"{reverse_label}({converter.thermal_flow})|flow_rate"
                outputs[output_name] = DataPointTimeSeries(
                    value=(
                        all_timeseries.get(forward_col, pd.Series(0.0, index=all_timeseries.index))
                        - all_timeseries.get(reverse_col, pd.Series(0.0, index=all_timeseries.index))
                    ).rename(output_name)
                )
                continue

            outputs[output_name] = DataPointTimeSeries(
                value = (all_timeseries[f"{converter.label}({converter.thermal_flow})|flow_rate"]
                * all_timeseries[f"{converter.label}|status"]
            ).rename(output_name))
            if isinstance(converter, FlixOptCHPConverter):
                output_name = converter.label + "_electrical_power"
                outputs[output_name] = DataPointTimeSeries(
                    value = (all_timeseries[
                        f"{converter.label}({converter.electrical_flow})|flow_rate"]
                    * all_timeseries[f"{converter.label}|status"]
                ).rename(output_name))

        for sink_source in self.flixopt_model.exchangers:
            label_inflow = f"{sink_source.label}({sink_source.input_bus}_in)|flow_rate"
            if label_inflow in all_timeseries.columns:
                output_name = sink_source.label + "_input"
                outputs[output_name] = DataPointTimeSeries(
                    value = all_timeseries[label_inflow].rename(output_name))
            label_outflow = f"{sink_source.label}({sink_source.output_bus}_out)|flow_rate"
            if label_outflow in all_timeseries.columns:
                output_name = sink_source.label + "_output"
                outputs[output_name] = DataPointTimeSeries(
                    value = all_timeseries[label_outflow].rename(output_name))

        self.output_data = FlixoptModelComponentOutputData.model_validate(outputs)

    def calculate(self) -> None:
        """
        Perform the calculations for the new component
        """

        # Prepare Input Data
        self.prepare_input_data()

        # Run Optimization
        optimization_results = self.run_optimization()

        if optimization_results is None:
            logger.error("Optimization failed.")
            return

        # Prepare the results and set the output data
        self.prepare_output_data(results=optimization_results)
