"""Unit tests for runtime and dispatch behavior of FlixoptModelComponent.

The focus is on model loading, converter dispatching, and optimization success
and failure paths.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)
from encodapy.components.flixopt_model_component.flixopt_model_component_config import (
    DataPointFlixoptModelConfig,
)
from encodapy.components.flixopt_model_component.flixopt_models import (
    FlixOptConverter,
    FlixOptConverterTypes,
    FlixoptLogLevel,
)


def _create_component() -> Any:
    """Create a bare FlixoptModelComponent test instance."""
    component = FlixoptModelComponent.__new__(FlixoptModelComponent)
    setattr(component, "_bidirectional_substations", {})
    setattr(component, "constraint_function", None)
    setattr(component, "manual_elements_function", None)
    return component


def _minimal_model_dict() -> dict[str, Any]:
    """Create a minimal valid model dictionary."""
    return {
        "buses": [{"label": "gas"}, {"label": "heat"}],
        "effects": [{"label": "costs", "unit": "EUR"}],
        "converters": [
            {
                "label": "boiler_1",
                "converter_type": FlixOptConverterTypes.BOILER,
                "thermal_efficiency": 0.9,
                "input_flow": "gas_in",
                "thermal_flow": "heat_out",
                "thermal_nominal_power": 100,
            }
        ],
        "exchangers": [],
        "storages": [],
    }


def test_prepare_component_loads_model_from_dict() -> None:
    """Load the model successfully from a dictionary payload."""
    component = _create_component()
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            flixopt_model=DataPointFlixoptModelConfig.model_validate(
                {"value": _minimal_model_dict()}
            ),
        ),
    )

    getattr(component, "prepare_component")()

    assert getattr(component, "flixopt_model") is not None


def test_get_converters_skips_invalid_chp_entry() -> None:
    """Skip an invalid CHP entry while building converters."""
    component = _create_component()
    invalid_chp = FlixOptConverter.model_validate(
        {
            "label": "chp_broken",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "input_flow": "gas_in",
            "thermal_flow": "heat_out",
            "thermal_nominal_power": 100,
        }
    )
    setattr(component, "flixopt_model", SimpleNamespace(converters=[invalid_chp]))

    converters = getattr(component, "_get_converters")()

    assert converters == []


def test_add_bidirectional_constraints_raises_when_coords_missing() -> None:
    """Raise when bidirectional constraints cannot access model coordinates."""
    component = _create_component()
    forward = SimpleNamespace(inputs=[SimpleNamespace(submodel=SimpleNamespace(flow_rate=1))])
    reverse = SimpleNamespace(inputs=[SimpleNamespace(submodel=SimpleNamespace(flow_rate=1))])
    setattr(component, "_bidirectional_substations", {"sub_a": (forward, reverse, 1.0, 1.0)})

    optimization = SimpleNamespace(model=SimpleNamespace(get_coords=lambda: None))

    with pytest.raises(ValueError, match="coordinates are not available"):
        getattr(component, "_add_bidirectional_substation_constraints")(optimization)


def test_run_optimization_returns_none_on_modeling_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return None when the modeling step fails."""
    component = _create_component()
    flow_system = SimpleNamespace(add_elements=lambda element: None)

    setattr(component, "_prepare_flixopt_flow_system", lambda: flow_system)
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "_add_bidirectional_substation_constraints", lambda optimization: None)
    setattr(component, "flixopt_model", SimpleNamespace())
    setattr(component, "config_data", SimpleNamespace(get_solver=lambda: "dummy"))

    class FakeOptimization:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.results = SimpleNamespace(summary={"Main Results": {"Objective": 0}})
            self.durations = {"modeling": 0.1, "solving": 0.2}

        def do_modeling(self) -> None:
            raise ValueError("broken model")

    monkeypatch.setattr(
        "encodapy.components.flixopt_model_component.flixopt_model_component.fx.Optimization",
        FakeOptimization,
    )

    result = getattr(component, "run_optimization")()

    assert result is None


def test_run_optimization_returns_none_on_solver_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return None when the solver raises a runtime error."""
    component = _create_component()
    flow_system = SimpleNamespace(add_elements=lambda element: None)

    setattr(component, "_prepare_flixopt_flow_system", lambda: flow_system)
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "_add_bidirectional_substation_constraints", lambda optimization: None)
    setattr(component, "flixopt_model", SimpleNamespace())
    setattr(component, "config_data", SimpleNamespace(get_solver=lambda: "dummy"))

    class FakeOptimization:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.results = SimpleNamespace(summary={"Main Results": {"Objective": 0}})
            self.durations = {"modeling": 0.1, "solving": 0.2}

        def do_modeling(self) -> None:
            return None

        def solve(self, _solver: str, log_main_results: bool = False) -> None:
            del log_main_results
            raise RuntimeError("solver failed")

    monkeypatch.setattr(
        "encodapy.components.flixopt_model_component.flixopt_model_component.fx.Optimization",
        FakeOptimization,
    )

    result = getattr(component, "run_optimization")()

    assert result is None


def test_run_optimization_returns_results_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return the results object after a successful optimization run."""
    component = _create_component()
    flow_system = SimpleNamespace(add_elements=lambda element: None)

    setattr(component, "_prepare_flixopt_flow_system", lambda: flow_system)
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "_add_bidirectional_substation_constraints", lambda optimization: None)
    setattr(component, "flixopt_model", SimpleNamespace())
    setattr(component, "config_data", SimpleNamespace(get_solver=lambda: "dummy"))

    fake_results = SimpleNamespace(summary={"Main Results": {"Objective": 7.0}})

    class FakeOptimization:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.results = fake_results
            self.durations = {"modeling": 0.1, "solving": 0.2}

        def do_modeling(self) -> None:
            return None

        def solve(self, _solver: str, log_main_results: bool = False) -> None:
            del log_main_results
            return None

    monkeypatch.setattr(
        "encodapy.components.flixopt_model_component.flixopt_model_component.fx.Optimization",
        FakeOptimization,
    )

    result = getattr(component, "run_optimization")()

    assert result is fake_results


def test_get_converters_dispatches_all_supported_types() -> None:
    """Dispatch all supported converter types in the expected order."""
    component = _create_component()

    boiler = SimpleNamespace(label="boiler", converter_type=FlixOptConverterTypes.BOILER)
    p2h = SimpleNamespace(label="p2h", converter_type=FlixOptConverterTypes.POWER2HEAT)
    chp_invalid = FlixOptConverter.model_validate(
        {
            "label": "chp_like",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "input_flow": "gas",
            "thermal_flow": "heat",
            "thermal_nominal_power": 10,
        }
    )
    substation = SimpleNamespace(label="sub", converter_type=FlixOptConverterTypes.SUBSTATION)
    bidir = SimpleNamespace(label="bidir", converter_type=FlixOptConverterTypes.BIDIRECTIONAL_SUBSTATION)
    unknown = SimpleNamespace(label="x", converter_type="unknown")

    setattr(
        component,
        "flixopt_model",
        SimpleNamespace(converters=[boiler, p2h, chp_invalid, substation, bidir, unknown]),
    )
    setattr(component, "_add_boiler_converter", lambda conv: f"boiler:{conv.label}")
    setattr(component, "_add_p2h_converter", lambda conv: f"p2h:{conv.label}")
    setattr(component, "_add_substation_converter", lambda conv: f"sub:{conv.label}")
    setattr(component, "_add_bidirectional_substation_converter", lambda conv: [f"bidir:{conv.label}:a", f"bidir:{conv.label}:b"])

    converters = getattr(component, "_get_converters")()

    assert converters == [
        "boiler:boiler",
        "p2h:p2h",
        "sub:sub",
        "bidir:bidir:a",
        "bidir:bidir:b",
    ]
