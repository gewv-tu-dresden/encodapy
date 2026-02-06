"""
Defines the FlixOptModelComponent class to perform optimizations using the FlixOpt library.
"""
# pylint: disable=no-member
from typing import Optional, Union, Any
from pydantic import ValidationError
import pandas as pd
import numpy as np
import xarray
import flixopt as fx # type: ignore[import-untyped]
from loguru import logger
from encodapy.components.basic_component import BasicComponent
from .flixopt_models import (
    FlixOptModel,
    FLIXOPT_CONFIG_MAP,
    FlixOptConverterTypes,
    FlixOptConverter,
    FlixOptCHPConverter,
    EnergyDirection,
    FlixOptSinkSource
)

from .flixopt_model_component_config import (
    FlixoptModelComponentInputData,
    FlixoptModelComponentOutputData,
    FlixoptModelComponentConfigData,
    DataPointTimeSeries
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
        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )
        self.config_data: FlixoptModelComponentConfigData
        self.input_data: FlixoptModelComponentInputData
        self.output_data: FlixoptModelComponentOutputData

        self.flixopt_model: FlixOptModel

        self.df_input: Optional[pd.DataFrame] = None

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        # Example: Initialize FlixOpt model or other resources here

        # Set flixopt log level based on configuration
        FLIXOPT_CONFIG_MAP[self.config_data.log_level.value]()

        #TODO This needs to be adapted for a productiv setup
        with open("02_flixopt_model_config.json", "r", encoding="utf-8") as file:
            model_config_json = file.read()
        self.flixopt_model = FlixOptModel.model_validate_json(model_config_json)


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

    def _get_input_value(self,
                         label:str) -> float | int:
        """
        Get a single input value from the input data based on the label
        Args:
            label (str): Label of the input value to retrieve
        Returns:
            float | int : The value of the input if found
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

        if not isinstance(input_data[label].get("value"), (float, int)):
            logger.error(f"Input value for label {label} is not a float or int.")
            raise ValueError(f"Input value for label {label} is not a float or int.")

        return input_data[label].get("value")

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
                    label = effect.label,
                    unit = effect.unit,
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
        return fx.Flow(
            label=converter.thermal_flow,
            bus=converter.thermal_flow,
            size=converter.thermal_nominal_power,
            relative_minimum=converter.thermal_power_range.min_power/100,
            relative_maximum=converter.thermal_power_range.max_power/100,
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
        return fx.StatusParameters(
            min_uptime=converter.status_parameters.min_up_time,
            max_uptime=converter.status_parameters.max_up_time,
            min_downtime=converter.status_parameters.min_down_time,
            max_downtime=converter.status_parameters.max_down_time,
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
            label = converter.label,
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
            electrical_flow= self._add_input_flow_to_converter(converter)
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

    def _get_converters(self) : #-> list[fx.Component]:
        """
        Prepare the FlixOpt components based on the model definition

        Returns:
            list[fx.Component]: List of FlixOpt components for the optimization
        """
        converters: list[fx.Component] = [] #TODO: add type hinting

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
                    converters.append(
                        self._add_chp_converter(converter)
                    )
                case _:
                    logger.warning(
                        f"Converter type {converter.converter_type} not supported yet."
                    )

        return converters

    def _get_storages(self) -> list[fx.Storage]:
        """
        Prepare the FlixOpt storage components based on the model definition

        Returns:
            list[fx.Component]: List of FlixOpt storage components for the optimization

        TODO: should we set a final capacity
        """
        storages = []

        for storage in self.flixopt_model.storages:
            if isinstance(storage.start_soc, str):
                initial_soc = self._get_input_value(storage.start_soc) / 100 \
                    * storage.nominal_capacity
            elif isinstance(storage.start_soc, (float, int)):
                initial_soc = storage.start_soc / 100 * storage.nominal_capacity
            # should not happen due to validation, but just in case
            else:
                initial_soc = 0

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
                    capacity_in_flow_hours=storage.nominal_capacity,
                    eta_charge=storage.eta_charge / 100 if storage.eta_charge is not None else None,
                    eta_discharge=storage.eta_discharge / 100 if storage.eta_discharge is not None \
                        else None,
                    relative_loss_per_hour=storage.relative_self_discharge / 100 \
                        if storage.relative_self_discharge is not None else None,
                    prevent_simultaneous_charge_and_discharge=True,
                    initial_charge_state=initial_soc
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

        # Define Sinks and Sources
        sinks_and_sources = self._get_sinks_and_sources()

        # Select components to be included in the flow system
        for element in converters + sinks_and_sources + storages:
            flow_system.add_elements(element)

        # Solve Problem
        try:
            optimization = fx.Optimization('encodapy', flow_system) # TODO do we need a name?
            optimization.do_modeling()
            optimization.solve(self.config_data.get_solver(), log_main_results=False)
        except Exception as e: #TODO
            logger.error(f"Error during optimization: {e}")
            print(type(e).__name__, e)
        logger.debug("Optimization completed with a "
                     f"duration for modeling {optimization.durations.get("modeling", '-')} s "
                     f"and solving {optimization.durations.get("solving", '-')} s.")
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
            freq=self.df_input.index.freq)
        all_timeseries.set_index("time", inplace=True)
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
        
        Args:
            all_timeseries (pd.DataFrame): DataFrame containing all timeseries

        TODO: 
            - Do we need more?
            - Should we use pd.Series instead of DataFrames for the output variables,
            but than we need to update the encodapy core

        """
        all_timeseries = self.export_results_as_timeseries(results.solution)

        #TODO make the mapping configurable

        # print(all_timeseries.columns)
        # print(all_timeseries)
        outputs: dict[str, pd.DataFrame]= {}
        for storage in self.flixopt_model.storages:
            outputs[storage.label + "_soc"] = \
                all_timeseries.filter([f"{storage.label}|charge_state"])

        for converter in self.flixopt_model.converters:

            outputs[converter.label + "_thermal_power"] = (
                all_timeseries[f"{converter.label}({converter.thermal_flow})|flow_rate"]
                * all_timeseries[f"{converter.label}|status"]
            ).to_frame(name=f"{converter.label}_thermal_power")
            if isinstance(converter, FlixOptCHPConverter):
                outputs[converter.label + "_electrical_power"] = (
                    all_timeseries[f"{converter.label}({converter.electrical_flow})|flow_rate"]
                    * all_timeseries[f"{converter.label}|status"]
                ).to_frame(name=f"{converter.label}_electrical_power")

        self.output_data = FlixoptModelComponentOutputData.model_validate(outputs)
        # print(self.output_data)

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
