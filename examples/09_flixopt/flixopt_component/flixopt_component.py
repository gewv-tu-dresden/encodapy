"""
Defines the FlixOptComponent class as example of a component using FlixOpt.
"""
from typing import Optional, Union
import pandas as pd
import numpy as np
import flixopt as fx # type: ignore[import-untyped]
from loguru import logger
from encodapy.components.basic_component import BasicComponent
from encodapy.utils.units import DataUnits
from .flixopt_component_config import (
    FlixoptComponentInputData,
    FlixoptComponentOutputData,
    FlixoptComponentConfigData,
    DataPointTimeSeries,
    FLIXOPT_CONFIG_MAP
)


class FlixoptComponent(BasicComponent):
    """
    Class for a FlixOpt component
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
        self.config_data: FlixoptComponentConfigData
        self.input_data: FlixoptComponentInputData
        self.output_data: FlixoptComponentOutputData

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        # Example: Initialize FlixOpt model or other resources here

        # Set flixopt log level based on configuration
        FLIXOPT_CONFIG_MAP[self.config_data.flixopt_log_level.value]()


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

    def run_optimization(self) -> None:
        """
        Perform the calculations for the new component
        """
        # Randbedingungen und Parameter
        check_penalty = False
        excess_penalty = 1e5
        use_chp_with_piecewise_conversion = False
        time_indices = None

        # Berechnung nach https://flixopt.github.io/flixopt/latest/examples/02-Complex%20Example/

        # --- Prepare Input Data ---
        df_input = self.prepare_input_data()
        if df_input is None:
            logger.error("Failed to prepare input data for optimization.")
            return

        # --- Define the Flow System, that will hold all elements, and the time steps you want to model ---
        # print(df_input.index)
        flow_system = fx.FlowSystem(df_input.index)  # Create FlowSystem

        flow_system.add_elements(
            fx.Bus('electricity', excess_penalty_per_flow_hour=excess_penalty),
            fx.Bus('heat', excess_penalty_per_flow_hour=excess_penalty),
            fx.Bus('gas', excess_penalty_per_flow_hour=excess_penalty),
        )
        # --- Define Effects ---
        # Specify effects related to costs, CO2 emissions, and primary energy consumption
        Costs = fx.Effect(
            'costs',
            '€', #TODO define unit for price ??
            'Kosten',
            is_standard=True,
            is_objective=True,
            share_from_temporal={'CO2': 0.2})
        CO2 = fx.Effect('CO2', 'kg', 'CO2_e-Emissionen')
        PE = fx.Effect('PE', 'kWh_PE', 'Primärenergie', maximum_total=3.5e3)
        
        # --- Define Components ---
        # 1. Define Boiler Component
        # A gas boiler that converts fuel into thermal output, with investment and on-off parameters
        gas_boiler = fx.linear_converters.Boiler(
            'Boiler',
            thermal_efficiency=0.5,  # Efficiency ratio
            on_off_parameters=fx.OnOffParameters(
                effects_per_running_hour={Costs.label: 0, CO2.label: 1000}
            ),  # CO2 emissions per hour
            thermal_flow=fx.Flow(
                label='Q_th',  # Thermal output
                bus='heat',  # Linked bus
                size=fx.InvestParameters(
                    effects_of_investment=1000,  # Fixed investment costs
                    fixed_size=50,  # Fixed size
                    mandatory=True,  # Forced investment
                    effects_of_investment_per_size={Costs.label: 10, PE.label: 2},  # Specific costs
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
                    consecutive_on_hours_min=np.array([1]*len(df_input.index)),  # min consecutive operation hours
                    consecutive_off_hours_max=10,  # Max consecutive off hours
                    effects_per_switch_on=0.01,  # Cost per switch-on
                    switch_on_max=1000,  # Max number of starts
                ),
            ),
            fuel_flow=fx.Flow(label='Q_fu', bus='gas', size=200),
        )

        # 2. Define CHP Unit
        # Combined Heat and Power unit that generates both electricity and heat from fuel
        bhkw = fx.linear_converters.CHP(
            'BHKW',
            thermal_efficiency=0.5,
            electrical_efficiency=0.4,
            on_off_parameters=fx.OnOffParameters(effects_per_switch_on=0.01),
            electrical_flow=fx.Flow('P_el', bus='electricity', size=60, relative_minimum=5 / 60),
            thermal_flow=fx.Flow('Q_th', bus='heat', size=1e3),
            fuel_flow=fx.Flow('Q_fu', bus='gas', size=1e3, previous_flow_rate=20),  # The CHP was ON previously
        )

        # 3. Define CHP with Piecewise Conversion
        # This CHP unit uses piecewise conversion for more dynamic behavior over time
        P_el = fx.Flow('P_el', bus='electricity', size=60, previous_flow_rate=20)
        Q_th = fx.Flow('Q_th', bus='heat')
        Q_fu = fx.Flow('Q_fu', bus='gas')
        piecewise_conversion = fx.PiecewiseConversion(
            {
                P_el.label: fx.Piecewise([fx.Piece(5, 30), fx.Piece(40, 60)]),
                Q_th.label: fx.Piecewise([fx.Piece(6, 35), fx.Piece(45, 100)]),
                Q_fu.label: fx.Piecewise([fx.Piece(12, 70), fx.Piece(90, 200)]),
            }
        )

        bhkw_2 = fx.LinearConverter(
            'BHKW2',
            inputs=[Q_fu],
            outputs=[P_el, Q_th],
            piecewise_conversion=piecewise_conversion,
            on_off_parameters=fx.OnOffParameters(effects_per_switch_on=0.01),
        )

        # 4. Define Storage Component
        # Storage with variable size and piecewise investment effects
        segmented_investment_effects = fx.PiecewiseEffects(
            piecewise_origin=fx.Piecewise([fx.Piece(5, 25), fx.Piece(25, 100)]),
            piecewise_shares={
                Costs.label: fx.Piecewise([fx.Piece(50, 250), fx.Piece(250, 800)]),
                PE.label: fx.Piecewise([fx.Piece(5, 25), fx.Piece(25, 100)]),
            },
        )

        thermal_storage = fx.Storage(
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
        )

        # 5. Define Sinks and Sources
        # 5.a) Heat demand profile
        heat_demand = fx.Sink(
            'heat_demand',
            inputs=[
                fx.Flow(
                    'Q_th_Last',  # Heat sink
                    bus='heat',  # Linked bus
                    size=1,
                    fixed_relative_profile=self._get_input_arrays(df_input, 0),  # Fixed demand profile
                )
            ],
        )
        electricity_demand = fx.Sink(
            'electricity_demand',
            inputs=[
                fx.Flow(
                    'P_el_Last',  # Electricity sink
                    bus='electricity',  # Linked bus
                    size=1,
                    fixed_relative_profile=self._get_input_arrays(df_input, 1),  # Fixed demand profile
                )
            ],
        )

        # 5.b) Gas tariff
        gas_demand = fx.Source(
            'gas_demand',
            outputs=[
                fx.Flow(
                    'Q_Gas',
                    bus='gas',  # Gas source
                    size=1000,  # Nominal size
                    effects_per_flow_hour={Costs.label: 0.04, CO2.label: 0.3},
                )
            ],
        )

        # 5.c) Feed-in of electricity
        electricity_feed_in = fx.Sink(
            'electricity_feed_in',
            inputs=[
                fx.Flow(
                    'P_el',
                    bus='electricity',  # Feed-in tariff for electricity
                    effects_per_flow_hour=-1 * self._get_input_arrays(df_input, 2),  # Negative price for feed-in
                )
            ],
        )

        # --- Build FlowSystem ---
        # Select components to be included in the flow system
        # flow_system.add_elements(Costs, CO2, PE, gas_boiler, heat_demand, gas_demand, electricity_feed_in, thermal_storage)
        flow_system.add_elements(Costs, CO2, PE, gas_boiler, heat_demand, gas_demand, electricity_demand, electricity_feed_in, thermal_storage)
        flow_system.add_elements(bhkw_2) if use_chp_with_piecewise_conversion else flow_system.add_elements(bhkw)

        # print(flow_system)  # Get a string representation of the FlowSystem

        # --- Solve FlowSystem ---
        optimization = fx.Optimization('complex example', flow_system, time_indices)

        optimization.do_modeling()

        optimization.solve(fx.solvers.HighsSolver(0.01, 60))

        # --- Ergebnisse auslesen ---
        solution = optimization.results.solution
        
        # logger.debug(f"Solution type: {type(solution)}")
        # logger.debug(f"Available variables: {list(solution.data_vars)}")
        # logger.debug(f"Dimensions: {solution.dims}")
        
        # Zeitreihen extrahieren
        results_dict = {}
        
        for var_name in solution.data_vars:
            # Konvertiere xarray DataArray zu pandas Series/DataFrame
            data_array = solution[var_name]
            
            if 'time' in data_array.dims:
                # Zeitreihe zu pandas Series/DataFrame konvertieren
                df = data_array.to_dataframe()
                results_dict[var_name] = df
                # logger.info(f"Variable '{var_name}': shape={df.shape}")
            else:
                # Skalare Werte
                value = data_array.values
                results_dict[var_name] = value
                # logger.info(f"Variable '{var_name}': {value}")
        
        # Alle Zeitreihen in einem DataFrame kombinieren (optional)
        all_timeseries = pd.DataFrame()
        for var_name, data in results_dict.items():
            if isinstance(data, (pd.DataFrame, pd.Series)):
                if isinstance(data, pd.DataFrame):
                    # Flatten MultiIndex columns wenn vorhanden
                    data = data.reset_index(drop=False)
                all_timeseries[var_name] = data if isinstance(data, pd.Series) else data.iloc[:, -1]
        
        # logger.info(f"\n{all_timeseries}")
        # print(all_timeseries.columns)
        
        df_results = pd.DataFrame(index=all_timeseries.index)
        df_results = df_results.iloc[:-1]
        df_results["time"] = df_input.index
        df_results["boiler_heat_output"] = all_timeseries["Boiler(Q_th)|flow_rate"] * all_timeseries["Boiler(Q_th)|on"]
        df_results["chp_heat_output"] = all_timeseries["BHKW(Q_th)|flow_rate"] * all_timeseries["BHKW(Q_th)|on"]
        df_results["chp_electric_output"] = all_timeseries["BHKW(P_el)|flow_rate"] * all_timeseries["BHKW(P_el)|on"]
        df_results["thermal_storage_charge_state"] = all_timeseries["thermal_storage|charge_state"]
        
        df_results = df_results.set_index("time")
        df_results = df_results.round(2)
        # print(df_results)

        self.output_data = FlixoptComponentOutputData(
            boiler_heat_output=DataPointTimeSeries(
                value=df_results["boiler_heat_output"],
                unit=DataUnits.WHR
            ),
            chp_heat_output=DataPointTimeSeries(
                value=df_results["chp_heat_output"],
                unit=DataUnits.WHR
            ),
            chp_electric_output=DataPointTimeSeries(
                value=df_results["chp_electric_output"],
                unit=DataUnits.WHR
            ),
            thermal_storage_charge_state=DataPointTimeSeries(
                value=df_results["thermal_storage_charge_state"]
            ),
        )
        #TODO maybe as dict --> so we can use it as a command input later?

    def calculate(self) -> None:
        """
        Perform the calculations for the new component
        """
        try:
            self.run_optimization()
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
