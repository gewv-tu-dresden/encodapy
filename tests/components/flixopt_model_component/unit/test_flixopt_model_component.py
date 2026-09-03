"""Regression tests for the FlixOpt model component."""

from typing import Any, cast

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)


def test_calculate_clears_stale_output_data_on_failed_optimization() -> None:
    """A failed optimization must not reuse output from the previous run."""

    component = FlixoptModelComponent.__new__(FlixoptModelComponent)
    runtime_component = cast(Any, component)
    runtime_component.output_data = object()
    runtime_component.prepare_input_data = lambda: None
    runtime_component.run_optimization = lambda: None

    component.calculate()

    assert not hasattr(component, "output_data")
