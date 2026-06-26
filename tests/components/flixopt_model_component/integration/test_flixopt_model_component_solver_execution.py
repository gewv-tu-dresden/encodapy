"""Integration test for executing the Flixopt component with a real solver."""

from __future__ import annotations

from typing import Any
import importlib.util

import pandas as pd
import pytest

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)
from encodapy.components.flixopt_model_component.flixopt_model_component_config import (
    FlixoptModelComponentConfigData,
)


class _InputDataStub:
    """Minimal input-data stub compatible with component internals."""

    def __init__(self, values: dict[str, dict[str, Any]]) -> None:
        self._values = values

    def __iter__(self):
        return iter(self._values.items())

    def model_dump(self) -> dict[str, dict[str, Any]]:
        return self._values


def _highs_solver_available() -> bool:
    """Return True when the optional Highs Python package is installed."""
    return importlib.util.find_spec("highspy") is not None


def _minimal_model_dict() -> dict[str, Any]:
    """Create a small but valid FlixOpt model for a stable solver e2e run."""
    return {
        "buses": [
            {"label": "gas_bus"},
            {"label": "heat_bus"},
        ],
        "effects": [
            {"label": "costs", "unit": "EUR", "objective": True},
        ],
        "converters": [
            {
                "label": "boiler_1",
                "converter_type": "boiler",
                "thermal_efficiency": 0.9,
                "input_flow": "gas_bus",
                "thermal_flow": "heat_bus",
                "thermal_nominal_power": 80,
                "thermal_power_range": {"min_power": 0, "max_power": 100},
                "status_parameters": {},
            }
        ],
        "exchangers": [
            {
                "label": "heat_demand_sink",
                "direction": "sink",
                "input_bus": "heat_bus",
                "input_label": "heat_demand",
            },
            {
                "label": "fuel_source",
                "direction": "source",
                "output_bus": "gas_bus",
                "nominal_power": 200,
                "output_effects": {"costs": "gas_price"},
            },
        ],
        "storages": [],
    }


def _create_component() -> FlixoptModelComponent:
    """Create a configured FlixoptModelComponent test instance."""
    component = FlixoptModelComponent.__new__(FlixoptModelComponent)
    setattr(component, "_bidirectional_substations", {})
    setattr(component, "constraint_function", None)
    setattr(component, "manual_elements_function", None)

    config_data = FlixoptModelComponentConfigData.model_validate(
        {
            "log_level": {"value": "silent"},
            "solver_settings": {
                "value": {
                    "name": "HighsSolver",
                    "mip_rel_gap": 0.05,
                    "time_limit": 10,
                }
            },
            "flixopt_model": {"value": _minimal_model_dict()},
        }
    )
    setattr(component, "config_data", config_data)
    return component


@pytest.mark.integration
def test_calculate_runs_solver_and_provides_boiler_output() -> None:
    """Run a full component calculation with Highs and verify robust invariants."""
    if not _highs_solver_available():
        pytest.skip("Optional dependency highspy is not installed.")

    component = _create_component()
    getattr(component, "prepare_component")()

    index = pd.date_range("2026-01-01", periods=4, freq="h")
    input_values = {
        "heat_demand": {"value": pd.Series([20.0, 30.0, 25.0, 15.0], index=index)},
        "gas_price": {"value": pd.Series([0.08, 0.08, 0.08, 0.08], index=index)},
    }
    setattr(component, "input_data", _InputDataStub(input_values))

    getattr(component, "calculate")()

    assert hasattr(component, "output_data")

    output_data = getattr(component, "output_data")
    thermal_power = output_data.boiler_1_thermal_power.value

    # Depending on solver/export shape, the last step may already be absent or dropped explicitly.
    assert len(thermal_power) in {len(index) - 1, len(index)}
    assert thermal_power.index.isin(index).all()
    assert (thermal_power >= -1e-6).all()
    assert (thermal_power <= 80.0 + 1e-6).all()
    assert thermal_power.notna().all()
