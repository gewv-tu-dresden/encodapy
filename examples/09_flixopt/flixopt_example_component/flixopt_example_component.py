"""
Defines the FlixOptComponent class as example of a component using FlixOpt.
"""
# pylint: disable=no-member
from typing import Optional, Union
import pandas as pd
import numpy as np
import xarray
import flixopt as fx # type: ignore[import-untyped]
from loguru import logger
from encodapy.components.basic_component import BasicComponent
from encodapy.utils.units import DataUnits
from .flixopt_example_component_config import (
    FlixoptExampleComponentInputData,
    FlixoptExampleComponentOutputData,
    FlixoptExampleComponentConfigData,
    DataPointTimeSeries,
    FLIXOPT_CONFIG_MAP,
    FlixOptEffects
)


class FlixoptExampleComponent(BasicComponent):
    """
    Class for a FlixOpt component
    
    This example show how to set up a flixopt model based on the flixopt examples: \
            https://flixopt.github.io/flixopt/latest/examples/02-Complex%20Example/
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
        self.config_data: FlixoptExampleComponentConfigData
        self.input_data: FlixoptExampleComponentInputData
        self.output_data: FlixoptExampleComponentOutputData

        # Component-specific initialization logic


    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        # Example: Initialize FlixOpt model or other resources here

        # Set flixopt log level based on configuration
        FLIXOPT_CONFIG_MAP[self.config_data.log_level.value]()


    def _get_input_arrays(self,
                          df_input:pd.DataFrame,
                          column:int) -> np.ndarray:
        return df_input[df_input.columns[column]].to_numpy()

    def prepare_input_data(self) -> Optional[pd.DataFrame]:
        """
        Prepare the input data for the FlixOpt component
        - Merge input time series into a single DataFrame
        - Ensure proper datetime index and frequency
        - Remove timezone information
        
        Returns:
            Optional[pd.DataFrame]: Prepared input data for optimization \
                or None if preparation fails
        """
        df_input = (
            self.input_data.heat_demand.value.rename('heat_demand').to_frame()
            .join(self.input_data.electricity_demand.value.rename('electricity_demand'))
            .join(self.input_data.electricity_price.value.rename('electricity_price'))
        )
        if not isinstance(self.input_data.heat_demand.value.index, pd.DatetimeIndex):
            logger.error("Input time series must have a DatetimeIndex")
            # should not happen due to validation
            return None
        freq: Optional[Union[str, pd.offsets.BaseOffset]] = \
            self.input_data.heat_demand.value.index.freq

        if freq is None:
            freq = pd.infer_freq(self.input_data.heat_demand.value.index)
        if freq is None:
            freq = pd.offsets.Hour(1)
            logger.warning("Could not infer frequency of input time series. Defaulting to 1H.")

        df_input.index = pd.DatetimeIndex(df_input.index, freq=freq)
        df_input.index = df_input.index.tz_localize(None)

        return df_input

    def _prepare_flixopt_flow_system(self,
                                     timesteps:pd.DatetimeIndex
                                     ) -> fx.FlowSystem:
        """
        Prepare the FlixOpt model for the optimization
        
        This part needs to be adjusted based on the specific model \
            you want to implement.
        Args:
            timesteps (pd.DatetimeIndex): Time steps for the FlowSystem
        Returns:
            fx.FlowSystem: Configured FlowSystem for optimization
        """
        #TODO make excess penalty configurable?
        excess_penalty = self.config_data.excess_penalty.value

        # --- Define the Flow System, that will hold all elements,
        # and the time steps you want to model ---

        flow_system = fx.FlowSystem(timesteps)

        flow_system.add_elements(
            fx.Bus('electricity', excess_penalty_per_flow_hour=excess_penalty),
            fx.Bus('heat', excess_penalty_per_flow_hour=excess_penalty),
            fx.Bus('gas', excess_penalty_per_flow_hour=excess_penalty),
        )

        return flow_system
    def _prepare_flixopt_effects(self) -> FlixOptEffects:
        """
        Prepare the FlixOpt effects, in a energy system usually costs, CO2 and PE
        
        Returns:
            FlixOptEffects: Configured effects for the optimization
        """
        #TODO make effects configurable?

        costs = fx.Effect(
            'costs',
            '€',
            'Kosten',
            is_standard=True,
            is_objective=True,
            share_from_temporal={'CO2': 0.2})
        co2 = fx.Effect('CO2', 'kg', 'CO2_e-Emissionen')
        pe = fx.Effect('PE', 'kWh_PE', 'Primärenergie', maximum_total=3.5e3)

        return FlixOptEffects(costs=costs, co2=co2, pe=pe)

    def run_optimization(self,
                         df_input:pd.DataFrame
                         ) -> fx.results.Results:
        """
        Perform the calculations with the FlixOpt library
            The model is built up in this function based on the input data \
                and the model structure defined here.
        
        Args:
            df_input (pd.DataFrame): Prepared input data for optimization
        Returns:
            fx.results.Results: Results from FlixOpt optimization        
        """
        # Check input data
        try:
            assert df_input is not None, "Input data preparation failed."
            assert isinstance(df_input.index, pd.DatetimeIndex), \
             "Input time series must have a DatetimeIndex"
        except AssertionError as e:
            logger.error(f"Error in input data: {e}")
            return

        flow_system = self._prepare_flixopt_flow_system(timesteps=df_input.index)
        # --- Define Effects ---
        effects = self._prepare_flixopt_effects()

        # --- Define Components ---
        components:list[fx.Component] = []
        # Define Boiler Component
        # A gas boiler that converts fuel into thermal output, with investment and on-off parameters
        components.append(fx.linear_converters.Boiler(
            'boiler',
            thermal_efficiency=0.5,  # Efficiency ratio
            on_off_parameters=fx.OnOffParameters(
                effects_per_running_hour={effects.costs.label: 0, effects.co2.label: 1000}
            ),  # CO2 emissions per hour
            thermal_flow=fx.Flow(
                label='Q_th',  # Thermal output
                bus='heat',  # Linked bus
                size=fx.InvestParameters(
                    effects_of_investment=1000,  # Fixed investment costs
                    fixed_size=50,  # Fixed size
                    mandatory=True,  # Forced investment
                    effects_of_investment_per_size={
                        effects.costs.label: 10, effects.pe.label: 2},  # Specific costs
                ),
                load_factor_max=1.0,  # Maximum load factor (50 kW)
                load_factor_min=0.1,  # Minimum load factor (5 kW)
                relative_minimum=5 / 50,  # Minimum part load
                relative_maximum=1,  # Maximum part load
                previous_flow_rate=50,  # Previous flow rate
                flow_hours_max=1e6,  # Total energy flow limit
                on_off_parameters=fx.OnOffParameters(
                    on_hours_min=0,  # Minimum operating hours
                    on_hours_max=1000,  # Maximum operating hours
                    consecutive_on_hours_max=10,  # Max consecutive operating hours
                    consecutive_on_hours_min=np.array([1]*len(df_input.index)), \
                        # min consecutive operation hours
                    consecutive_off_hours_max=10,  # Max consecutive off hours
                    effects_per_switch_on=0.01,  # Cost per switch-on
                    switch_on_max=1000,  # Max number of starts
                ),
            ),
            fuel_flow=fx.Flow(label='Q_fu', bus='gas', size=200),
        ))

        # Define CHP with Piecewise Conversion
        # This CHP unit uses piecewise conversion for more dynamic behavior over time
        p_el = fx.Flow('P_el', bus='electricity', size=60, previous_flow_rate=20)
        q_th = fx.Flow('Q_th', bus='heat')
        q_fu = fx.Flow('Q_fu', bus='gas')
        piecewise_conversion = fx.PiecewiseConversion(
            {
                p_el.label: fx.Piecewise([fx.Piece(5, 30), fx.Piece(40, 60)]),
                q_th.label: fx.Piecewise([fx.Piece(6, 35), fx.Piece(45, 100)]),
                q_fu.label: fx.Piecewise([fx.Piece(12, 70), fx.Piece(90, 200)]),
            }
        )

        components.append(fx.LinearConverter(
            'chp',
            inputs=[q_fu],
            outputs=[p_el, q_th],
            piecewise_conversion=piecewise_conversion,
            on_off_parameters=fx.OnOffParameters(effects_per_switch_on=0.01),
        ))

        # Define Storage Component
        # Storage with variable size and piecewise investment effects
        segmented_investment_effects = fx.PiecewiseEffects(
            piecewise_origin=fx.Piecewise([fx.Piece(5, 25), fx.Piece(25, 100)]),
            piecewise_shares={
                effects.costs.label: fx.Piecewise([fx.Piece(50, 250), fx.Piece(250, 800)]),
                effects.pe.label: fx.Piecewise([fx.Piece(5, 25), fx.Piece(25, 100)]),
            },
        )
        storages: list[fx.Storage] = []
        storages.append(fx.Storage(
            'thermal_storage',
            charging=fx.Flow('Q_th_load', bus='heat', size=1e4),
            discharging=fx.Flow('Q_th_unload', bus='heat', size=1e4),
            capacity_in_flow_hours=fx.InvestParameters(
                piecewise_effects_of_investment=segmented_investment_effects,  # Investment effects
                mandatory=True,  # Forced investment
                minimum_size=0,
                maximum_size=1000,  # Optimizing between 0 and 1000 kWh
            ),
            initial_charge_state=0,  # Initial charge state
            maximal_final_charge_state=10,  # Maximum final charge state
            eta_charge=0.9,
            eta_discharge=1,  # Charge/discharge efficiency
            relative_loss_per_hour=0.08,  # Energy loss per hour, relative to current charge state
            prevent_simultaneous_charge_and_discharge=True,  # Prevent simultaneous charge/discharge
        ))

        # Define Sinks and Sources
        # Heat demand profile
        sind_and_sources: list[Union[fx.Sink, fx.Source]] = []

        sind_and_sources.append(fx.Sink(
            'heat_demand',
            inputs=[
                fx.Flow(
                    'Q_th_Last',  # Heat sink
                    bus='heat',  # Linked bus
                    size=1,
                    fixed_relative_profile=self._get_input_arrays(df_input, 0),
                )
            ],
        ))
        sind_and_sources.append(fx.Sink(
            'electricity_demand',
            inputs=[
                fx.Flow(
                    'P_el_Last',  # Electricity sink
                    bus='electricity',  # Linked bus
                    size=1,
                    fixed_relative_profile=self._get_input_arrays(df_input, 1),
                )
            ],
        ))

        # Gas tariff
        sind_and_sources.append(fx.Source(
            'gas_demand',
            outputs=[
                fx.Flow(
                    'Q_Gas',
                    bus='gas',  # Gas source
                    size=1000,  # Nominal size
                    effects_per_flow_hour={effects.costs.label: 0.04, effects.co2.label: 0.3},
                )
            ],
        ))

        # Feed-in of electricity
        sind_and_sources.append(fx.Sink(
            'electricity_feed_in',
            inputs=[
                fx.Flow(
                    'P_el',
                    bus='electricity',  # Feed-in tariff for electricity
                    effects_per_flow_hour=-1 * self._get_input_arrays(df_input, 2), \
                        # Negative price for feed-in
                )
            ],
        ))

        # --- Build FlowSystem ---
        # Select components to be included in the flow system
        flow_system.add_elements(effects.costs, effects.co2, effects.pe)
        for component in components:
            flow_system.add_elements(component)
        for sink_or_source in sind_and_sources:
            flow_system.add_elements(sink_or_source)
        for storage in storages:
            flow_system.add_elements(storage)

        # --- Solve FlowSystem ---
        optimization = fx.Optimization('Example', flow_system)
        optimization.do_modeling()
        optimization.solve(self.config_data.get_solver())

        return optimization.results

    def export_results(self,
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
        return all_timeseries

    def prepare_output_data(self,
                            all_timeseries: pd.DataFrame,
                            timesteps:pd.DatetimeIndex) -> None:
        """
        Prepare the output data for the FlixOpt component, mapping results to output model
        
        Args:
            all_timeseries (pd.DataFrame): DataFrame containing all timeseries
            
        TODO: 
            - Make the mapping configurable --> via config file / component config \
                and connect it to the configuration?
            - Maybe build the output as dict --> so we can use it as a command input later?
        
        """
        result_mapping = {
            "converter": {
                "boiler": "boiler",
                "chp": "chp"
            },
            "storage": {
                "thermal_storage": "thermal_storage"
            }
        }
        df_results = pd.DataFrame(index=all_timeseries.index)
        df_results = df_results.iloc[:-1]
        df_results["time"] = timesteps
        for key, value in result_mapping["converter"].items():
            for energy_type in ["Q_th", "P_el"]:
                key_complet = f"{value}({energy_type})"
                key_energy = "thermal" if energy_type == "Q_th" else "electric"

                if f"{key_complet}|flow_rate" in all_timeseries.columns:
                    df_results[f"{key}_{key_energy}_energy"] = \
                        all_timeseries[f"{key_complet}|flow_rate"] \
                            * all_timeseries[f"{key_complet}|on"]

        for key, value in result_mapping["storage"].items():
            df_results[f"{key}_charge_state"] = all_timeseries[f"{value}|charge_state"]

        df_results = df_results.set_index("time")
        df_results = df_results.round(2)

        self.output_data = FlixoptExampleComponentOutputData(
            boiler_heat_output=DataPointTimeSeries(
                value=df_results["boiler_thermal_energy"],
                unit=DataUnits.WHR
            ),
            chp_heat_output=DataPointTimeSeries(
                value=df_results["chp_thermal_energy"],
                unit=DataUnits.WHR
            ),
            chp_electric_output=DataPointTimeSeries(
                value=df_results["chp_electric_energy"],
                unit=DataUnits.WHR
            ),
            thermal_storage_charge_state=DataPointTimeSeries(
                value=df_results["thermal_storage_charge_state"]
            ),
        )


    def calculate(self) -> None:
        """
        Perform the calculations for the new component
        """

        # --- Prepare Input Data ---
        df_input = self.prepare_input_data()
        try:
            assert df_input is not None, "Input data preparation failed."
            assert isinstance(df_input.index, pd.DatetimeIndex), \
             "Input time series must have a DatetimeIndex"
        except AssertionError as e:
            logger.error(f"Error in input data: {e}")
            return
        # --- Run Optimization ---
        optimization_results = self.run_optimization(df_input=df_input)

        # --- Get the results ---
        results = self.export_results(optimization_results.solution)
        self.prepare_output_data(all_timeseries=results, timesteps=df_input.index)
