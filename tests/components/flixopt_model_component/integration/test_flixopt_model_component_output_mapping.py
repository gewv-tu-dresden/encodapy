"""Integration-style tests for result export and output mapping.

The tests verify the derivation of domain outputs from optimization results,
including the special case of bidirectional substations.
"""

from types import SimpleNamespace
from typing import Any

import pandas as pd
import xarray as xr

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)
from encodapy.components.flixopt_model_component.flixopt_models import (
    EnergyDirection,
    FlixOptConverterTypes,
    FlixOptModel,
)


def _create_component() -> Any:
    """Create a bare FlixoptModelComponent test instance."""
    component = FlixoptModelComponent.__new__(FlixoptModelComponent)
    input_index = pd.date_range("2026-01-01", periods=3, freq="h")
    setattr(component, "df_input", pd.DataFrame(index=input_index))
    setattr(component, "df_input_timezone", input_index.tz)
    setattr(component, "_bidirectional_substations", {})
    return component


def test_prepare_output_data_uses_forward_minus_reverse() -> None:
    """Compute bidirectional output using forward minus reverse flow rates."""
    component: Any = _create_component()
    time_index = pd.date_range("2026-01-01", periods=3, freq="h")
    all_timeseries = pd.DataFrame(
        {
            "sub_a_fwd(heat_bus)|flow_rate": [10.0, 5.0, 8.0],
            "sub_a_rev(heat_bus)|flow_rate": [3.0, 1.0, 5.0],
        },
        index=time_index,
    )

    converter = SimpleNamespace(label="sub_a", thermal_flow="heat_bus")
    setattr(
        component,
        "flixopt_model",
        SimpleNamespace(
            storages=[],
            converters=[converter],
            exchangers=[],
        ),
    )
    setattr(component, "_bidirectional_substations", {
        "sub_a": (
            SimpleNamespace(label="sub_a_fwd"),
            SimpleNamespace(label="sub_a_rev"),
            1.0,
            1.0,
        )
    })

    setattr(component, "export_results_as_timeseries", lambda results: all_timeseries)

    getattr(component, "prepare_output_data")(results=SimpleNamespace(solution=None))

    output_data = getattr(component, "output_data")
    output_series = getattr(output_data, "sub_a_thermal_power").value
    expected = pd.Series([7.0, 4.0, 3.0], index=time_index, name="sub_a_thermal_power")

    pd.testing.assert_series_equal(output_series, expected)


def test_export_results_as_timeseries_removes_last_row_and_preserves_index_tz() -> None:
    """Drop the last time step and preserve the timezone of the exported index."""
    component: Any = _create_component()
    input_index = pd.date_range("2026-01-01", periods=4, freq="h", tz="UTC")
    setattr(component, "df_input", pd.DataFrame(index=input_index))
    setattr(component, "df_input_timezone", input_index.tz)

    results = xr.Dataset(
        data_vars={"status": ("time", [1.0, 0.0, 1.0, 0.0])},
        coords={"time": input_index},
    )

    result = getattr(component, "export_results_as_timeseries")(results)

    assert len(result) == 3
    assert result.index.tz is not None
    assert str(result.index.tz) == "UTC"


def test_prepare_output_data_maps_storage_and_converter_outputs() -> None:
    """Map storage and converter outputs into the prepared result model."""
    component: Any = _create_component()
    time_index = pd.date_range("2026-01-01", periods=3, freq="h")
    all_timeseries = pd.DataFrame(
        {
            "battery|charge_state": [20.0, 25.0, 30.0],
            "boiler_1(heat_out)|flow_rate": [10.0, 11.0, 12.0],
            "boiler_1|status": [1.0, 1.0, 0.0],
        },
        index=time_index,
    )

    setattr(component, "flixopt_model", FlixOptModel.model_validate(
        {
            "buses": [
                {"label": "heat"},
            ],
            "effects": [
                {"label": "costs", "unit": "EUR"},
            ],
            "converters": [
                {
                    "label": "boiler_1",
                    "converter_type": FlixOptConverterTypes.BOILER,
                    "thermal_efficiency": 0.9,
                    "input_flow": "gas_in",
                    "thermal_flow": "heat_out",
                    "thermal_nominal_power": 100,
                    "thermal_power_range": {"min_power": 0, "max_power": 100},
                    "status_parameters": {},
                }
            ],
            "exchangers": [
                {
                    "label": "exchange_1",
                    "direction": EnergyDirection.SINK,
                    "input_bus": "heat_in",
                    "nominal_power": 25,
                }
            ],
            "storages": [
                {
                    "label": "battery",
                    "bus": "heat",
                    "nominal_power": 25,
                    "nominal_capacity": 100,
                    "start_soc": 50,
                    "minimal_soc": 10,
                    "maximal_soc": 90,
                }
            ],
        }
    ))
    setattr(component, "_bidirectional_substations", {})
    setattr(component, "export_results_as_timeseries", lambda results: all_timeseries)

    getattr(component, "prepare_output_data")(results=SimpleNamespace(solution=None))

    output_data = getattr(component, "output_data")
    assert getattr(output_data, "battery_soc").value.tolist() == [20.0, 25.0, 30.0]
    assert getattr(output_data, "boiler_1_thermal_power").value.tolist() == [10.0, 11.0, 0.0]
