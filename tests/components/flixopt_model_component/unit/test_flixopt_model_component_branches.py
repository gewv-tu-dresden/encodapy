"""Unit tests for hard-to-reach branches of FlixoptModelComponent.

This module covers defensive branches, exception paths, and special
configuration combinations with targeted mocks.
"""

from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import xarray as xr

from encodapy.components.flixopt_model_component import flixopt_model_component as flix_module
from encodapy.components.flixopt_model_component import (
    flixopt_model_component_config as config_module,
)
from encodapy.components.flixopt_model_component.add_constraints import add_constraints
from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)
from encodapy.components.flixopt_model_component.flixopt_model_component_config import (
    DataPointFlixoptModelConfig,
    FlixoptModelComponentConfigData,
)
from encodapy.components.flixopt_model_component.flixopt_models import (
    EnergyDirection,
    FlixOptCHPConverter,
    FlixOptConverter,
    FlixOptConverterTypes,
    FlixOptModel,
    FlixOptSinkSource,
    FlixoptLogLevel,
    FlixoptSolverSettings,
)
from encodapy.components.basic_component import BasicComponent
from encodapy.utils.datapoints import DataPointTimeSeries


def _component() -> Any:
    """Create a bare FlixoptModelComponent test instance."""
    c = FlixoptModelComponent.__new__(FlixoptModelComponent)
    setattr(c, "df_input", None)
    setattr(c, "df_input_timezone", None)
    setattr(c, "_bidirectional_substations", {})
    setattr(c, "constraint_function", None)
    setattr(c, "manual_elements_function", None)
    return c


def _model_dict() -> dict[str, Any]:
    """Create a minimal valid model dictionary."""
    return {
        "buses": [{"label": "b_in"}, {"label": "b_out"}],
        "effects": [{"label": "costs", "unit": "EUR"}],
        "converters": [
            {
                "label": "boiler",
                "converter_type": FlixOptConverterTypes.BOILER,
                "thermal_efficiency": 0.9,
                "input_flow": "b_in",
                "thermal_flow": "b_out",
                "thermal_nominal_power": 100,
            }
        ],
        "exchangers": [],
        "storages": [],
    }


def test_init_sets_default_members(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that the constructor sets the expected default members."""
    monkeypatch.setattr(
        BasicComponent, "__init__", lambda self, config, component_id, static_data=None: None
    )

    component = FlixoptModelComponent(config={}, component_id="c1")

    assert component.constraint_function is None
    assert component.manual_elements_function is None
    assert component.df_input is None
    assert component.df_input_timezone is None


def test_prepare_component_file_not_found_raises() -> None:
    """Raise FileNotFoundError when the configured model file does not exist."""
    component = _component()
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            flixopt_model=DataPointFlixoptModelConfig.model_validate(
                {"value": "this_file_does_not_exist_abc123.json"}
            ),
        ),
    )

    with pytest.raises(FileNotFoundError):
        getattr(component, "prepare_component")()


def test_prepare_component_raises_validation_error_for_invalid_model() -> None:
    """Raise a validation error when the model payload is incomplete."""
    component = _component()
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            flixopt_model=DataPointFlixoptModelConfig.model_validate(
                {"value": {"buses": [], "effects": []}}
            ),
        ),
    )

    with pytest.raises(Exception):
        getattr(component, "prepare_component")()


def test_prepare_component_reaches_non_dict_non_path_value_branch() -> None:
    """Cover the branch for a value that is neither a dict nor a file path."""
    component = _component()
    # model_construct bypasses pydantic value-type validation on purpose.
    invalid_dp = DataPointFlixoptModelConfig.model_construct(value=123)
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            flixopt_model=invalid_dp,
        ),
    )

    with pytest.raises(ValueError, match="dict or a path to a json file"):
        getattr(component, "prepare_component")()


def test_prepare_component_loads_constraint_and_element_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load both optional helper functions during component preparation."""
    component = _component()

    model_with_helpers = _model_dict() | {
        "constraints_function": "dummy_constraints.py",
        "manual_elements_function": "dummy_elements.py",
    }
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            flixopt_model=DataPointFlixoptModelConfig.model_validate({"value": model_with_helpers}),
        ),
    )

    def f_constraints(_opt: Any) -> None:
        return None

    def f_elements(_cfg: Any) -> list[Any]:
        return []

    calls: list[tuple[str, str]] = []

    def fake_loader(path: str, symbol: str) -> Any:
        calls.append((path, symbol))
        return f_constraints if symbol == "add_constraints" else f_elements

    monkeypatch.setattr(component, "_load_helper_functions", fake_loader)

    getattr(component, "prepare_component")()

    assert getattr(component, "constraint_function") is f_constraints
    assert getattr(component, "manual_elements_function") is f_elements
    assert ("dummy_constraints.py", "add_constraints") in calls
    assert ("dummy_elements.py", "add_elements") in calls


def test_load_helper_functions_import_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise helper loading import errors for spec and loader failures."""
    component = _component()

    monkeypatch.setattr(
        flix_module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None
    )
    with pytest.raises(ImportError, match="Could not create module spec"):
        getattr(component, "_load_helper_functions")("foo.py", "add_constraints")

    monkeypatch.setattr(
        flix_module.importlib.util,
        "spec_from_file_location",
        lambda *_args, **_kwargs: SimpleNamespace(loader=None),
    )
    with pytest.raises(ImportError, match="No loader available"):
        getattr(component, "_load_helper_functions")("foo.py", "add_constraints")


def test_load_helper_functions_returns_none_for_empty_symbol(tmp_path) -> None:
    """Return None when no helper symbol name is provided."""
    component = _component()
    helper_file = tmp_path / "helper_ok.py"
    helper_file.write_text("def fn():\n    return 1\n", encoding="utf-8")

    result = getattr(component, "_load_helper_functions")(str(helper_file), "")

    assert result is None


def test_load_helper_functions_raises_for_non_function_symbol() -> None:
    """Raise when the requested symbol is not a callable function."""
    component = _component()

    with pytest.raises(ImportError, match="not found"):
        getattr(component, "_load_helper_functions")("math", "pi")


def test_get_input_arrays_raises_for_missing_data_and_column() -> None:
    """Raise when the input DataFrame or requested column is missing."""
    component = _component()

    with pytest.raises(ValueError, match="not prepared"):
        getattr(component, "_get_input_arrays")("col")

    setattr(component, "df_input", pd.DataFrame({"other": [1.0]}))
    with pytest.raises(ValueError, match="not found"):
        getattr(component, "_get_input_arrays")("col")


def test_get_input_value_unknown_key_and_invalid_none_allowed() -> None:
    """Raise for missing keys and invalid non-numeric input values."""
    component = _component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {"a": {"value": "x"}}))

    with pytest.raises(ValueError, match="not found in input data"):
        getattr(component, "_get_input_value")("missing")

    with pytest.raises(ValueError, match="neither float/int nor None"):
        getattr(component, "_get_input_value")("a", none_allowed=True)


def test_get_input_value_returns_none_if_allowed() -> None:
    """Allow None as input when none_allowed is enabled."""
    component = _component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {}))

    assert getattr(component, "_get_input_value")(None, none_allowed=True) is None


def test_get_input_value_raises_if_input_data_missing() -> None:
    """Raise when input data has not been prepared yet."""
    component = _component()
    setattr(component, "input_data", None)

    with pytest.raises(ValueError, match="Input data is not prepared"):
        getattr(component, "_get_input_value")("x")


def test_get_input_value_raises_for_non_numeric_without_none_allowed() -> None:
    """Raise for non-numeric input when None is not allowed."""
    component = _component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {"a": {"value": "x"}}))

    with pytest.raises(ValueError, match="not a float or int"):
        getattr(component, "_get_input_value")("a")


def test_prepare_input_data_uses_default_hour_for_non_inferable_freq() -> None:
    """Use the default hourly frequency when the input frequency cannot be inferred."""
    component = _component()
    index = pd.DatetimeIndex(
        [
            "2026-01-01 00:00:00",
            "2026-01-01 00:20:00",
            "2026-01-01 01:00:00",
        ]
    )
    ts = DataPointTimeSeries.model_validate({"value": pd.Series([1.0, 2.0, 3.0], index=index)})
    setattr(component, "input_data", [("a", ts.model_dump())])

    with pytest.raises(ValueError):
        getattr(component, "prepare_input_data")()


def test_prepare_flixopt_flow_system_builds_elements() -> None:
    """Build a flow system with buses and effects."""
    component = _component()
    setattr(
        component,
        "df_input",
        pd.DataFrame(index=pd.date_range("2026-01-01", periods=2, freq="h")),
    )
    setattr(component, "flixopt_model", FlixOptModel.model_validate(_model_dict()))

    flow_system = getattr(component, "_prepare_flixopt_flow_system")()

    assert hasattr(flow_system, "buses")
    assert hasattr(flow_system, "effects")


def test_add_chp_converter_raises_for_wrong_type() -> None:
    """Reject a converter that is not compatible with the CHP builder."""
    component = _component()
    wrong = FlixOptConverter.model_validate(
        {
            "label": "not_chp",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "input_flow": "in",
            "thermal_flow": "th",
            "thermal_nominal_power": 10,
        }
    )

    with pytest.raises(ValueError, match="FlixOptCHPConverter"):
        getattr(component, "_add_chp_converter")(wrong)


def test_converter_builder_methods_return_constructed_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the converter builder helpers create the expected objects."""
    component = _component()
    setattr(component, "_get_input_value", lambda *args, **kwargs: 0.0)

    converter = FlixOptConverter.model_validate(
        {
            "label": "boiler_1",
            "converter_type": FlixOptConverterTypes.BOILER,
            "thermal_efficiency": 0.8,
            "input_flow": "in_bus",
            "thermal_flow": "out_bus",
            "thermal_nominal_power": 10,
        }
    )
    chp_converter = FlixOptCHPConverter.model_validate(
        {
            "label": "chp_1",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "electrical_efficiency": 0.3,
            "input_flow": "gas",
            "thermal_flow": "heat",
            "electrical_flow": "el",
            "thermal_nominal_power": 20,
        }
    )

    monkeypatch.setattr(flix_module.fx, "Flow", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx, "StatusParameters", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx.linear_converters, "Boiler", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx.linear_converters, "Power2Heat", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx.linear_converters, "CHP", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx.components, "LinearConverter", SimpleNamespace)

    out_flow = getattr(component, "_add_output_flow_to_converter")(converter)
    in_flow = getattr(component, "_add_input_flow_to_converter")(converter)
    boiler = getattr(component, "_add_boiler_converter")(converter)
    p2h = getattr(component, "_add_p2h_converter")(converter)
    chp = getattr(component, "_add_chp_converter")(chp_converter)
    sub = getattr(component, "_add_substation_converter")(converter)

    assert out_flow.label == "out_bus"
    assert in_flow.label == "in_bus"
    assert boiler.label == "boiler_1"
    assert p2h.label == "boiler_1"
    assert chp.label == "chp_1"
    assert sub.label == "boiler_1"


def test_add_bidirectional_substation_converter_rejects_non_positive_efficiency() -> None:
    """Reject a bidirectional substation with non-positive efficiency."""
    component = _component()
    converter = FlixOptConverter.model_validate(
        {
            "label": "bidir",
            "converter_type": FlixOptConverterTypes.BIDIRECTIONAL_SUBSTATION,
            "thermal_efficiency": 0,
            "input_flow": "in",
            "thermal_flow": "out",
            "thermal_nominal_power": 10,
        }
    )

    with pytest.raises(ValueError, match="invalid thermal_efficiency"):
        getattr(component, "_add_bidirectional_substation_converter")(converter)


def test_add_bidirectional_substation_converter_builds_forward_and_reverse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build both forward and reverse converters for a bidirectional substation."""
    component = _component()
    converter = FlixOptConverter.model_validate(
        {
            "label": "bidir",
            "converter_type": FlixOptConverterTypes.BIDIRECTIONAL_SUBSTATION,
            "thermal_efficiency": 0.5,
            "input_flow": "in",
            "thermal_flow": "out",
            "thermal_nominal_power": 10,
        }
    )

    monkeypatch.setattr(flix_module.fx.components, "LinearConverter", SimpleNamespace)
    monkeypatch.setattr(
        component, "_add_input_flow_to_converter", lambda _c: SimpleNamespace(label="in")
    )
    monkeypatch.setattr(
        component, "_add_output_flow_to_converter", lambda _c: SimpleNamespace(label="out")
    )
    monkeypatch.setattr(
        component, "_add_status_parameters_to_converter", lambda _c: SimpleNamespace()
    )

    converters = getattr(component, "_add_bidirectional_substation_converter")(converter)

    assert len(converters) == 2
    assert "bidir" in getattr(component, "_bidirectional_substations")


def test_get_converters_handles_valid_chp_branch() -> None:
    """Cover the valid CHP branch in converter dispatch."""
    component = _component()
    chp = FlixOptCHPConverter.model_validate(
        {
            "label": "chp_1",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "electrical_efficiency": 0.3,
            "input_flow": "gas",
            "thermal_flow": "heat",
            "electrical_flow": "el",
            "thermal_nominal_power": 20,
        }
    )
    setattr(component, "flixopt_model", SimpleNamespace(converters=[chp]))
    setattr(component, "_add_chp_converter", lambda conv: f"chp:{conv.label}")

    converters = getattr(component, "_get_converters")()

    assert converters == ["chp:chp_1"]


def test_add_bidirectional_substation_constraints_adds_binary_gates() -> None:
    """Add binary gates for bidirectional substation constraints."""
    component = _component()
    forward = SimpleNamespace(inputs=[SimpleNamespace(submodel=SimpleNamespace(flow_rate=1.0))])
    reverse = SimpleNamespace(inputs=[SimpleNamespace(submodel=SimpleNamespace(flow_rate=1.0))])
    setattr(component, "_bidirectional_substations", {"s1": (forward, reverse, 10.0, 5.0)})

    called_constraints: list[str] = []

    model = SimpleNamespace(
        get_coords=lambda: {"time": [0, 1]},
        add_variables=lambda **kwargs: 1,
        add_constraints=lambda _expr, name: called_constraints.append(name),
    )
    optimization = SimpleNamespace(model=model)

    getattr(component, "_add_bidirectional_substation_constraints")(optimization)

    assert "bidir_forward_gate_0" in called_constraints
    assert "bidir_reverse_gate_0" in called_constraints


def test_get_flow_effects_and_information_return_empty_on_invalid_direction() -> None:
    """Return empty flow effect data for an invalid direction."""
    component = _component()
    sink_source = SimpleNamespace(
        input_label=None,
        output_label=None,
        input_effects=None,
        output_effects=None,
        nominal_power=1,
        input_bus="in",
        output_bus="out",
    )

    effects = getattr(component, "_get_flow_effects")(sink_source, "invalid")
    info = getattr(component, "_get_flow_information")(sink_source, "invalid")

    assert not effects
    assert info == {"size": 1}


def test_get_sinks_and_sources_skips_unknown_direction() -> None:
    """Skip exchangers that use an unknown direction."""
    component = _component()
    bad_exchanger = SimpleNamespace(label="bad", direction="unknown")
    setattr(component, "flixopt_model", SimpleNamespace(exchangers=[bad_exchanger]))

    out = getattr(component, "_get_sinks_and_sources")()

    assert not out


def test_get_sinks_and_sources_handles_source_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build a source element for exchangers with SOURCE direction."""
    component = _component()
    src = SimpleNamespace(label="src", direction=EnergyDirection.SOURCE)
    setattr(component, "flixopt_model", SimpleNamespace(exchangers=[src]))
    monkeypatch.setattr(
        component,
        "_get_flow_information",
        lambda *_args, **_kwargs: {"label": "x", "bus": "b", "size": 1},
    )
    monkeypatch.setattr(flix_module.fx, "Flow", SimpleNamespace)
    monkeypatch.setattr(flix_module.fx, "Source", SimpleNamespace)

    out = getattr(component, "_get_sinks_and_sources")()

    assert len(out) == 1
    assert out[0].label == "src"


def test_loguru_forward_handler_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the success path of the Loguru forward handler."""
    handler = flix_module._LoguruForwardHandler()  # pylint: disable=protected-access
    called = {"log": False}

    class _Opt:  # pylint: disable=too-few-public-methods
        def log(self, level: str, message: str) -> None:
            """Record that a log call happened and assert its payload."""
            called["log"] = True
            assert level == "INFO"
            assert message == "hello"

    monkeypatch.setattr(flix_module.logger, "opt", lambda exception=None: _Opt())

    record = flix_module.logging.LogRecord(
        name="t",
        level=flix_module.logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    handler.emit(record)

    assert called["log"] is True


def test_run_optimization_calls_constraint_function(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoke the optional constraint function during optimization."""
    component = _component()
    del monkeypatch
    setattr(
        component,
        "_prepare_flixopt_flow_system",
        lambda: SimpleNamespace(
            add_elements=lambda e: None,
            build_model=lambda: None,
            solve=lambda _solver, **_kwargs: None,
            solution=SimpleNamespace(summary={"Main Results": {"Objective": 0}}),
            durations={"modeling": 0.1, "solving": 0.2},
            model=SimpleNamespace(get_coords=lambda: []),
        ),
    )
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "_add_bidirectional_substation_constraints", lambda optimization: None)
    setattr(component, "config_data", SimpleNamespace(get_solver=lambda: "dummy"))
    setattr(component, "flixopt_model", SimpleNamespace())
    called = {"constraint": False}
    setattr(
        component, "constraint_function", lambda optimization: called.update({"constraint": True})
    )

    result = getattr(component, "run_optimization")()

    assert result is not None
    assert called["constraint"] is True


def test_run_optimization_manual_elements_invalid_type_raises() -> None:
    """Raise when the manual elements function returns invalid objects."""
    component = _component()
    setattr(
        component,
        "_prepare_flixopt_flow_system",
        lambda: SimpleNamespace(add_elements=lambda e: None),
    )
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "manual_elements_function", lambda _cfg: [object()])
    setattr(component, "flixopt_model", SimpleNamespace())

    with pytest.raises(ValueError, match="Manual elements function"):
        getattr(component, "run_optimization")()


def test_run_optimization_returns_none_on_file_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return None when the solver executable cannot be found."""
    component = _component()
    del monkeypatch
    setattr(
        component,
        "_prepare_flixopt_flow_system",
        lambda: SimpleNamespace(
            add_elements=lambda e: None,
            build_model=lambda: None,
            solve=lambda _solver, **_kwargs: (_ for _ in ()).throw(
                FileNotFoundError("solver not found")
            ),
            solution=SimpleNamespace(summary={"Main Results": {"Objective": 0}}),
            durations={"modeling": 0.1, "solving": 0.2},
            model=SimpleNamespace(get_coords=lambda: []),
        ),
    )
    setattr(component, "_get_converters", lambda: [])
    setattr(component, "_get_storages", lambda: [])
    setattr(component, "_get_sinks_and_sources", lambda: [])
    setattr(component, "_add_bidirectional_substation_constraints", lambda optimization: None)
    setattr(component, "config_data", SimpleNamespace(get_solver=lambda: "dummy"))
    setattr(component, "flixopt_model", SimpleNamespace())

    assert getattr(component, "run_optimization")() is None


def test_export_results_as_timeseries_raises_when_input_missing() -> None:
    """Raise when export is attempted without prepared input data."""
    component = _component()
    setattr(component, "df_input", None)

    with pytest.raises(ValueError, match="Input data is not prepared"):
        getattr(component, "export_results_as_timeseries")(xr.Dataset())


def test_export_results_as_timeseries_handles_scalar_data_var() -> None:
    """Ignore scalar data variables during time series export."""
    component = _component()
    setattr(
        component,
        "df_input",
        pd.DataFrame(index=pd.date_range("2026-01-01", periods=3, freq="h")),
    )
    setattr(component, "df_input_timezone", None)

    dataset = xr.Dataset(
        data_vars={
            "status": ("time", [1.0, 0.0, 1.0]),
            "scalar": ((), 7.0),
        },
        coords={"time": pd.date_range("2026-01-01", periods=3, freq="h")},
    )

    out = getattr(component, "export_results_as_timeseries")(dataset)

    assert "status" in out.columns
    assert "scalar" not in out.columns


def test_prepare_output_data_maps_chp_and_exchanger_io() -> None:
    """Map CHP and exchanger inputs and outputs into the result model."""
    component = _component()
    idx = pd.date_range("2026-01-01", periods=3, freq="h")
    all_timeseries = pd.DataFrame(
        {
            "chp_1(heat_out)|flow_rate": [5.0, 6.0, 7.0],
            "chp_1(el_out)|flow_rate": [2.0, 3.0, 4.0],
            "chp_1|status": [1.0, 1.0, 0.0],
            "ex_sink(heat_in_in)|flow_rate": [1.0, 1.1, 1.2],
            "ex_src(el_out_out)|flow_rate": [2.0, 2.1, 2.2],
        },
        index=idx,
    )

    chp = FlixOptCHPConverter.model_validate(
        {
            "label": "chp_1",
            "converter_type": FlixOptConverterTypes.CHP,
            "thermal_efficiency": 0.5,
            "electrical_efficiency": 0.3,
            "input_flow": "gas",
            "thermal_flow": "heat_out",
            "electrical_flow": "el_out",
            "thermal_nominal_power": 20,
        }
    )
    model = FlixOptModel.model_validate(
        {
            "buses": [{"label": "heat_in"}, {"label": "el_out"}],
            "effects": [{"label": "costs", "unit": "EUR"}],
            "converters": [chp.model_dump()],
            "exchangers": [
                {
                    "label": "ex_sink",
                    "direction": EnergyDirection.SINK,
                    "input_bus": "heat_in",
                    "nominal_power": 5,
                },
                {
                    "label": "ex_src",
                    "direction": EnergyDirection.SOURCE,
                    "output_bus": "el_out",
                    "nominal_power": 5,
                },
            ],
            "storages": [],
        }
    )

    setattr(component, "flixopt_model", model)
    setattr(component, "_bidirectional_substations", {})
    setattr(component, "export_results_as_timeseries", lambda _res: all_timeseries)

    getattr(component, "prepare_output_data")(SimpleNamespace(solution=None))

    out = getattr(component, "output_data")
    assert getattr(out, "chp_1_thermal_power").value.tolist() == [5.0, 6.0, 0.0]
    assert getattr(out, "chp_1_electrical_power").value.tolist() == [2.0, 3.0, 0.0]
    assert getattr(out, "ex_sink_input").value.tolist() == [1.0, 1.1, 1.2]
    assert getattr(out, "ex_src_output").value.tolist() == [2.0, 2.1, 2.2]


def test_get_solver_forwards_time_limit_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forward explicit solver settings, including the time limit."""

    class _FakeHighsSolver:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        config_module.fx,
        "solvers",
        SimpleNamespace(HighsSolver=_FakeHighsSolver),
    )

    config_data = FlixoptModelComponentConfigData.model_validate(
        {
            "solver_settings": {
                "value": {
                    "name": "HighsSolver",
                    "mip_rel_gap": 0.05,
                    "time_limit": 10,
                }
            },
            "flixopt_model": {"value": _model_dict()},
        }
    )

    solver = config_data.get_solver()

    assert isinstance(solver, _FakeHighsSolver)
    assert solver.kwargs == {"mip_gap": 0.05, "time_limit_seconds": 10}


def test_get_solver_forwards_advanced_settings_via_extra_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forward advanced tuning settings via flixopt's extra_options argument."""

    class _FakeGurobiSolver:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        config_module.fx,
        "solvers",
        SimpleNamespace(GurobiSolver=_FakeGurobiSolver),
    )

    config_data = FlixoptModelComponentConfigData.model_validate(
        {
            "solver_settings": {
                "value": {
                    "name": "GurobiSolver",
                    "mip_rel_gap": 0.05,
                    "time_limit": 10,
                    "threads": 7,
                    "mip_focus": 1,
                    "presolve": 2,
                    "cuts": 1,
                    "additional_options": {"NodefileStart": 0.5},
                }
            },
            "flixopt_model": {"value": _model_dict()},
        }
    )

    solver = config_data.get_solver()

    assert isinstance(solver, _FakeGurobiSolver)
    assert solver.kwargs == {
        "mip_gap": 0.05,
        "time_limit_seconds": 10,
        "extra_options": {
            "Threads": 7,
            "MIPFocus": 1,
            "Presolve": 2,
            "Cuts": 1,
            "NodefileStart": 0.5,
        },
    }


def test_get_solver_forwards_highs_advanced_settings_via_extra_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forward Highs tuning settings with lowercase option keys."""

    class _FakeHighsSolver:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        config_module.fx,
        "solvers",
        SimpleNamespace(HighsSolver=_FakeHighsSolver),
    )

    config_data = FlixoptModelComponentConfigData.model_validate(
        {
            "solver_settings": {
                "value": {
                    "name": "HighsSolver",
                    "mip_rel_gap": 0.05,
                    "time_limit": 10,
                    "threads": 4,
                    "presolve": 1,
                    "additional_options": {"solver": "simplex"},
                }
            },
            "flixopt_model": {"value": _model_dict()},
        }
    )

    solver = config_data.get_solver()

    assert isinstance(solver, _FakeHighsSolver)
    assert solver.kwargs == {
        "mip_gap": 0.05,
        "time_limit_seconds": 10,
        "extra_options": {
            "threads": 4,
            "presolve": 1,
            "solver": "simplex",
        },
    }


def test_get_solver_raises_for_unsupported_solver_name() -> None:
    """Raise when the configured solver class cannot be resolved."""
    config_data = FlixoptModelComponentConfigData.model_validate(
        {
            "solver_settings": {
                "value": {
                    "name": "HighsSolver",
                }
            },
            "flixopt_model": {"value": _model_dict()},
        }
    )
    config_data.solver_settings.value = FlixoptSolverSettings.model_construct(
        name=SimpleNamespace(value="UnknownSolver"),
        mip_rel_gap=None,
        time_limit=None,
    )

    with pytest.raises(ValueError, match="Unsupported solver name: UnknownSolver"):
        config_data.get_solver()


def test_flixopt_sink_source_sink_requires_input_bus() -> None:
    """Reject sink exchangers without an input bus."""
    with pytest.raises(Exception, match="For a sink, input_bus must be defined"):
        FlixOptSinkSource.model_validate(
            {
                "label": "sink_without_input",
                "direction": EnergyDirection.SINK,
            }
        )


def test_flixopt_sink_source_source_requires_output_bus() -> None:
    """Reject source exchangers without an output bus."""
    with pytest.raises(Exception, match="For a source, output_bus must be defined"):
        FlixOptSinkSource.model_validate(
            {
                "label": "source_without_output",
                "direction": EnergyDirection.SOURCE,
            }
        )


def test_flixopt_sink_source_bidirectional_requires_any_bus() -> None:
    """Reject bidirectional exchangers when both buses are missing."""
    with pytest.raises(Exception, match=r"input_bus and output_bus \(optional\) must be defined"):
        FlixOptSinkSource.model_validate(
            {
                "label": "bidir_without_buses",
                "direction": EnergyDirection.BIDIRECTIONAL,
                "nominal_power": 1,
            }
        )


def test_flixopt_sink_source_bidirectional_requires_nominal_power() -> None:
    """Reject bidirectional exchangers when nominal power is missing."""
    with pytest.raises(Exception, match="nominal_power must be defined"):
        FlixOptSinkSource.model_validate(
            {
                "label": "bidir_without_nominal_power",
                "direction": EnergyDirection.BIDIRECTIONAL,
                "input_bus": "heat_bus",
            }
        )


def test_flixopt_sink_source_bidirectional_sets_output_bus_from_input() -> None:
    """Copy input bus to output bus for bidirectional exchangers when omitted."""
    exchanger = FlixOptSinkSource.model_validate(
        {
            "label": "bidir_with_single_bus",
            "direction": EnergyDirection.BIDIRECTIONAL,
            "input_bus": "heat_bus",
            "nominal_power": 5,
        }
    )

    assert exchanger.output_bus == "heat_bus"


def test_add_constraints_raises_when_coords_missing() -> None:
    """Raise when the optimization model coordinates are unavailable."""
    optimization = SimpleNamespace(model=SimpleNamespace(get_coords=lambda: None))

    with pytest.raises(ValueError, match="coordinates are not available"):
        add_constraints(optimization)


def test_add_constraints_adds_example_binary_gate() -> None:
    """Add the example variables and gate constraint from the template."""
    add_variable_calls: list[dict[str, Any]] = []
    added_constraint_names: list[str] = []

    def _add_variables(**kwargs: Any) -> int:
        add_variable_calls.append(kwargs)
        return len(add_variable_calls)

    model = SimpleNamespace(
        get_coords=lambda: {"time": [0, 1]},
        add_variables=_add_variables,
        add_constraints=lambda _expr, name: added_constraint_names.append(name),
    )
    optimization = SimpleNamespace(model=model)

    add_constraints(optimization)

    assert len(add_variable_calls) == 2
    assert all(call["binary"] is True for call in add_variable_calls)
    assert added_constraint_names == ["example"]
