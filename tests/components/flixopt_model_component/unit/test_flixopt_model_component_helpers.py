"""Unit tests for helper and data paths of FlixoptModelComponent.

The tests in this module focus on small helper functions, input parsing,
logging forwarding, and basic control-flow checks.
"""

import logging
from datetime import timezone
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pandas as pd
import pytest

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
    _LoguruForwardHandler,
)
from encodapy.components.flixopt_model_component.flixopt_models import (
    EnergyDirection,
    FlixOptConverter,
    FlixOptConverterTypes,
    FlixoptLogLevel,
    FlixOptModel,
    FlixOptStorage,
    _apply_production_preset,
)
from encodapy.utils.datapoints import DataPointTimeSeries


def _create_component() -> Any:
    """Create a bare FlixoptModelComponent test instance."""
    component = FlixoptModelComponent.__new__(FlixoptModelComponent)
    setattr(component, "df_input", None)
    setattr(component, "df_input_timezone", None)
    setattr(component, "_bidirectional_substations", {})
    return component


def _create_minimal_model() -> FlixOptModel:
    """Create a minimal valid FlixOptModel fixture."""
    return FlixOptModel.model_validate(
        {
            "buses": [
                {"label": "gas"},
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
                    "status_parameters": {"min_up_time": 2},
                }
            ],
            "exchangers": [],
            "storages": [
                {
                    "label": "storage_1",
                    "bus": "heat",
                    "nominal_power": 25,
                    "nominal_capacity": 100,
                    "start_soc": 50,
                    "minimal_soc": 10,
                    "maximal_soc": 90,
                }
            ],
        }
    )


def test_storage_rejects_negative_soc_safety_margin() -> None:
    """Reject a negative SOC margin instead of silently widening the limits."""
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        FlixOptStorage.model_validate(
            {
                "label": "storage_1",
                "bus": "heat",
                "nominal_power": 25,
                "nominal_capacity": 100,
                "soc_safety_margin": -5,
            }
        )


def test_get_input_value_returns_literal_numbers() -> None:
    """Return literal numeric inputs unchanged."""
    component: Any = _create_component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {}))

    assert getattr(component, "_get_input_value")(42) == 42
    assert getattr(component, "_get_input_value")(3.5) == 3.5


def test_get_input_value_returns_ndarray_for_series() -> None:
    """Convert a prepared Series input into a NumPy array."""
    component: Any = _create_component()
    index = pd.date_range("2026-01-01", periods=3, freq="h")
    series = pd.Series([1.0, 2.0, 3.0], index=index)
    setattr(component, "df_input", pd.DataFrame({"series_input": series}))
    setattr(
        component,
        "input_data",
        SimpleNamespace(model_dump=lambda: {"series_input": {"value": series}}),
    )

    result = getattr(component, "_get_input_value")(
        "series_input", ndarray_allowed=True
    )

    assert isinstance(result, np.ndarray)
    assert list(result) == [1.0, 2.0, 3.0]


def test_get_input_arrays_returns_column_values() -> None:
    """Return the values of a prepared input column."""
    component: Any = _create_component()
    setattr(
        component,
        "df_input",
        pd.DataFrame(
            {"series_input": [4.0, 5.0, 6.0]},
            index=pd.date_range("2026-01-01", periods=3, freq="h"),
        ),
    )

    result = getattr(component, "_get_input_arrays")("series_input")

    assert list(result) == [4.0, 5.0, 6.0]


def test_prepare_input_data_merges_series_and_strips_timezone() -> None:
    """Merge series inputs and remove timezone information from the index."""
    component: Any = _create_component()
    index = pd.date_range("2026-01-01", periods=3, freq="h", tz=timezone.utc)
    series_a = DataPointTimeSeries.model_validate(
        {"value": pd.Series([1.0, 2.0, 3.0], index=index)}
    )
    series_b = DataPointTimeSeries.model_validate(
        {"value": pd.Series([10.0, 20.0, 30.0], index=index)}
    )
    setattr(
        component,
        "input_data",
        [
            ("series_a", series_a.model_dump()),
            ("series_b", series_b.model_dump()),
        ],
    )

    getattr(component, "prepare_input_data")()

    df_input = cast(pd.DataFrame, getattr(component, "df_input"))
    assert df_input is not None
    assert list(df_input.columns) == ["series_a", "series_b"]
    assert isinstance(df_input.index, pd.DatetimeIndex)
    assert df_input.index.tz is None
    assert getattr(component, "df_input_timezone") is not None
    expected = pd.Series(
        [1.0, 2.0, 3.0],
        index=df_input.index,
        name="series_a",
    )
    series_out = cast(pd.Series, df_input.loc[:, "series_a"])
    pd.testing.assert_series_equal(series_out, expected)


def test_load_helper_functions_loads_python_module(tmp_path) -> None:
    """Load a helper function from a Python module file."""
    component: Any = _create_component()
    helper_file = tmp_path / "custom_constraints.py"
    helper_file.write_text(
        "def add_constraints(optimization, config):\n"
        "    return (optimization, config)\n",
        encoding="utf-8",
    )

    function = getattr(component, "_load_helper_functions")(
        str(helper_file), "add_constraints"
    )

    assert function is not None
    assert function.__name__ == "add_constraints"


def test_prepare_component_rejects_invalid_model_payload() -> None:
    """Reject a flixopt_model payload with an invalid value type."""
    component: Any = _create_component()
    setattr(
        component,
        "config_data",
        SimpleNamespace(
            log_level=SimpleNamespace(value=FlixoptLogLevel.SILENT),
            get_effective_log_level=lambda: FlixoptLogLevel.SILENT,
            flixopt_model=SimpleNamespace(value=123),
        ),
    )

    try:
        getattr(component, "prepare_component")()
    except ValueError as exc:
        assert "flixopt_model must be of type DataPointFlixoptModelConfig" in str(exc)
    else:
        raise AssertionError("prepare_component() did not raise ValueError")


def test_min_uptime_profile_is_reduced_for_carry_over_runtime() -> None:
    """Reduce the min_uptime profile for converters with carry-over runtime."""
    component: Any = _create_component()
    index = pd.date_range("2026-01-01", periods=4, freq="h")
    setattr(component, "df_input", pd.DataFrame(index=index))
    setattr(
        component,
        "input_data",
        SimpleNamespace(model_dump=lambda: {"operation_time": {"value": 1}}),
    )

    converter = FlixOptConverter.model_validate(
        {
            "label": "boiler_1",
            "converter_type": FlixOptConverterTypes.BOILER,
            "thermal_efficiency": 0.9,
            "input_flow": "gas_in",
            "thermal_flow": "heat_out",
            "thermal_nominal_power": 100,
            "thermal_power_range": {"min_power": 0, "max_power": 100},
            "status_parameters": {"min_up_time": 4},
            "operation_time": "operation_time",
        }
    )

    status_parameters = getattr(component, "_add_status_parameters_to_converter")(
        converter
    )

    assert status_parameters.min_uptime is not None
    assert list(status_parameters.min_uptime)[:2] == [3.0, 2.0]


def test_get_storages_clips_initial_soc_to_bounds() -> None:
    """Clamp the initial state of charge to the configured storage bounds."""
    component: Any = _create_component()
    setattr(
        component,
        "input_data",
        SimpleNamespace(
            model_dump=lambda: {
                "storage_capacity": {"value": 100},
                "storage_start": {"value": 80},
                "storage_min": {"value": 20},
                "storage_max": {"value": 60},
            }
        ),
    )
    setattr(
        component,
        "flixopt_model",
        FlixOptModel.model_validate(
            {
                "buses": [
                    {"label": "heat"},
                ],
                "effects": [
                    {"label": "costs", "unit": "EUR"},
                ],
                "converters": [],
                "exchangers": [],
                "storages": [
                    {
                        "label": "storage_1",
                        "bus": "heat",
                        "nominal_power": 25,
                        "nominal_capacity": "storage_capacity",
                        "start_soc": "storage_start",
                        "minimal_soc": "storage_min",
                        "maximal_soc": "storage_max",
                    }
                ],
            }
        ),
    )

    storages = getattr(component, "_get_storages")()

    assert len(storages) == 1
    assert storages[0].initial_charge_state == 60.0
    assert storages[0].relative_minimum_charge_state == 0.2
    assert storages[0].relative_maximum_charge_state == 0.6


def test_get_sinks_and_sources_builds_bidirectional_source_and_sink() -> None:
    """Build the bidirectional sink and source representation."""
    component: Any = _create_component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {}))
    setattr(
        component,
        "flixopt_model",
        FlixOptModel.model_validate(
            {
                "buses": [
                    {"label": "heat"},
                ],
                "effects": [
                    {"label": "costs", "unit": "EUR"},
                ],
                "converters": [],
                "exchangers": [
                    {
                        "label": "exchange_1",
                        "direction": EnergyDirection.BIDIRECTIONAL,
                        "nominal_power": 25,
                        "input_bus": "heat_in",
                        "output_bus": "heat_out",
                    }
                ],
                "storages": [],
            }
        ),
    )

    sinks_and_sources = getattr(component, "_get_sinks_and_sources")()

    assert len(sinks_and_sources) == 1
    assert sinks_and_sources[0].label == "exchange_1"


def test_loguru_forward_handler_handles_format_errors() -> None:
    """Exercise the error path of the Loguru forward handler."""

    class _FailingHandler(_LoguruForwardHandler):
        def __init__(self) -> None:
            super().__init__()
            self.handled = False

        def format(self, record: Any) -> str:
            raise TypeError("format failed")

        def handleError(self, record: Any) -> None:
            del record
            self.handled = True

    handler = _FailingHandler()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="msg",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert handler.handled is True


def test_configure_library_logging_routes_loggers_through_loguru() -> None:
    """Library loggers keep their own output, only forward to loguru.

    All own handlers (console/file handlers of the flixopt CONFIG presets)
    must be removed, records are forwarded at their original level, and the
    configuration must be repeatable without duplicating handlers.
    """
    # pylint: disable=protected-access
    cls = FlixoptModelComponent
    saved_state: dict[str, tuple[list, int, bool]] = {}
    for logger_name in ("flixopt", "flixopt.solver", "linopy"):
        library_logger = logging.getLogger(logger_name)
        saved_state[logger_name] = (
            list(library_logger.handlers),
            library_logger.level,
            library_logger.propagate,
        )

    try:
        # Simulate a flixopt preset having attached its own console handler.
        console_handler = logging.StreamHandler()
        logging.getLogger("flixopt").addHandler(console_handler)

        cls._configure_library_logging()
        cls._configure_library_logging()  # idempotent

        for logger_name in ("flixopt", "flixopt.solver", "linopy"):
            library_logger = logging.getLogger(logger_name)
            handlers = library_logger.handlers
            assert len(handlers) == 1
            assert isinstance(handlers[0], _LoguruForwardHandler)
            assert console_handler not in handlers
            assert library_logger.propagate is False
            assert library_logger.level == logging.DEBUG

        # Records are forwarded (not written directly and not propagated).
        forwarded: list[str] = []

        def _capture(message: Any) -> None:  # pragma: no cover - test helper
            forwarded.append(str(message))

        from loguru import logger as _logger

        sink_id = _logger.add(_capture, level="INFO")
        try:
            logging.getLogger("flixopt").info("forwarded flixopt record")
        finally:
            _logger.remove(sink_id)

        assert any("forwarded flixopt record" in line for line in forwarded)
    finally:
        for logger_name, (
            handlers,
            level,
            propagate,
        ) in saved_state.items():
            library_logger = logging.getLogger(logger_name)
            library_logger.handlers = handlers
            library_logger.setLevel(level)
            library_logger.propagate = propagate


def test_load_helper_functions_raises_for_missing_symbol(tmp_path) -> None:
    """Raise ImportError when the requested helper symbol is missing."""
    component: Any = _create_component()
    helper_file = tmp_path / "helper_module.py"
    helper_file.write_text("def some_other_name():\n    return 1\n", encoding="utf-8")

    try:
        getattr(component, "_load_helper_functions")(
            str(helper_file), "add_constraints"
        )
    except ImportError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Expected ImportError for missing symbol")


def test_get_input_value_raises_for_none_when_not_allowed() -> None:
    """Reject None when none_allowed is False."""
    component: Any = _create_component()
    setattr(component, "input_data", SimpleNamespace(model_dump=lambda: {}))

    try:
        getattr(component, "_get_input_value")(None, none_allowed=False)
    except ValueError as exc:
        assert "cannot be None" in str(exc)
    else:
        raise AssertionError("Expected ValueError for None input")


def test_prepare_input_data_returns_when_index_not_datetime() -> None:
    """Skip DataFrame preparation when the input index is not datetime-like."""
    component: Any = _create_component()
    setattr(component, "input_data", [("scalar", {"value": 1.0})])

    getattr(component, "prepare_input_data")()

    assert getattr(component, "df_input") is None


def test_prepare_flixopt_flow_system_raises_without_datetime_index() -> None:
    """Raise when the datetime-indexed input data is missing."""
    component: Any = _create_component()
    setattr(component, "df_input", None)

    try:
        getattr(component, "_prepare_flixopt_flow_system")()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError when df_input is missing")


def test_calculate_skips_output_preparation_when_optimization_fails() -> None:
    """Skip output preparation when optimization does not return results."""
    component: Any = _create_component()
    called = {"prepare_output": False}

    setattr(component, "prepare_input_data", lambda: None)
    setattr(component, "run_optimization", lambda: None)
    setattr(
        component,
        "prepare_output_data",
        lambda results: called.update({"prepare_output": True}),
    )

    getattr(component, "calculate")()

    assert called["prepare_output"] is False


def test_calculate_runs_output_preparation_on_success() -> None:
    """Run output preparation after a successful optimization."""
    component: Any = _create_component()
    called = {"prepare_output": False}
    fake_results = object()

    setattr(component, "prepare_input_data", lambda: None)
    setattr(component, "run_optimization", lambda: fake_results)

    def _prepare_output_data(results: Any) -> None:
        assert results is fake_results
        called["prepare_output"] = True

    setattr(component, "prepare_output_data", _prepare_output_data)

    getattr(component, "calculate")()

    assert called["prepare_output"] is True


def test_loguru_forward_handler_falls_back_to_numeric_level() -> None:
    """Unknown stdlib level names are forwarded at the numeric level."""
    from loguru import logger as _logger

    forwarded: list[str] = []

    def _capture(message: Any) -> None:  # pragma: no cover - test helper
        forwarded.append(str(message))

    record = logging.LogRecord(
        name="test",
        level=100,  # no registered name -> loguru can not resolve 'Level 100'
        pathname=__file__,
        lineno=1,
        msg="numeric fallback record",
        args=(),
        exc_info=None,
    )

    handler = _LoguruForwardHandler()
    sink_id = _logger.add(_capture, level=0)
    try:
        handler.emit(record)
    finally:
        _logger.remove(sink_id)

    assert any("numeric fallback record" in line for line in forwarded)


def test_production_preset_writes_no_logfile_to_cwd(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The production preset must not leave a flixopt.log in the working dir."""
    # pylint: disable=protected-access
    import os

    monkeypatch.chdir(tmp_path)

    _apply_production_preset()

    assert list(tmp_path.iterdir()) == []
    assert not os.path.exists("flixopt.log")


def test_loguru_forward_handler_reports_errors_when_all_forwards_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fall back to the handler error routine if loguru rejects all levels."""
    import encodapy.components.flixopt_model_component.flixopt_model_component as flix_module

    class _RaisingLogger:
        def opt(self, **_kwargs: Any) -> Any:
            return self

        def log(self, *_args: Any, **_kwargs: Any) -> None:
            raise ValueError("loguru rejected the level")

    class _TrackingHandler(flix_module._LoguruForwardHandler):
        def __init__(self) -> None:
            super().__init__()
            self.handled = False

        def handleError(self, record: Any) -> None:
            del record
            self.handled = True

    monkeypatch.setattr(flix_module, "logger", _RaisingLogger())

    handler = _TrackingHandler()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="unreportable record",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert handler.handled is True


def test_get_storages_raises_for_soc_below_bounds() -> None:
    """Raise when the effective minimal SOC is below the valid range."""
    component: Any = _create_component()
    setattr(
        component,
        "input_data",
        SimpleNamespace(
            model_dump=lambda: {
                "storage_capacity": {"value": 100},
                "storage_start": {"value": 50},
                "storage_min": {"value": -10},
                "storage_max": {"value": 80},
            }
        ),
    )
    setattr(
        component,
        "flixopt_model",
        FlixOptModel.model_validate(
            {
                "buses": [{"label": "heat"}],
                "effects": [{"label": "costs", "unit": "EUR"}],
                "converters": [],
                "exchangers": [],
                "storages": [
                    {
                        "label": "storage_1",
                        "bus": "heat",
                        "nominal_power": 25,
                        "nominal_capacity": "storage_capacity",
                        "start_soc": "storage_start",
                        "minimal_soc": "storage_min",
                        "maximal_soc": "storage_max",
                    }
                ],
            }
        ),
    )

    with pytest.raises(ValueError, match="invalid SOC limits"):
        getattr(component, "_get_storages")()


def test_get_storages_raises_for_min_soc_above_max_soc() -> None:
    """Raise when the effective minimal SOC is not below the maximal SOC."""
    component: Any = _create_component()
    setattr(
        component,
        "input_data",
        SimpleNamespace(
            model_dump=lambda: {
                "storage_capacity": {"value": 100},
                "storage_start": {"value": 50},
                "storage_min": {"value": 60},
                "storage_max": {"value": 50},
            }
        ),
    )
    setattr(
        component,
        "flixopt_model",
        FlixOptModel.model_validate(
            {
                "buses": [{"label": "heat"}],
                "effects": [{"label": "costs", "unit": "EUR"}],
                "converters": [],
                "exchangers": [],
                "storages": [
                    {
                        "label": "storage_1",
                        "bus": "heat",
                        "nominal_power": 25,
                        "nominal_capacity": "storage_capacity",
                        "start_soc": "storage_start",
                        "minimal_soc": "storage_min",
                        "maximal_soc": "storage_max",
                    }
                ],
            }
        ),
    )

    with pytest.raises(ValueError, match="minimal_soc >= maximal_soc"):
        getattr(component, "_get_storages")()
