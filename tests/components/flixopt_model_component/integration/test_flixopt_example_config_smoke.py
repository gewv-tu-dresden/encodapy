"""Smoke test for the 09_flixopt example configuration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)
from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.config.types import AttributeTypes
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    InputDataModel,
    StaticDataEntityModel,
)


def _highs_solver_available() -> bool:
    """Return True when the optional Highs Python package is installed."""
    return importlib.util.find_spec("highspy") is not None


def _example_dir() -> Path:
    """Return the absolute path to the flixopt example directory."""
    return Path(__file__).resolve().parents[4] / "examples" / "09_mpc_flixopt"


def _load_component_config(example_dir: Path) -> ControllerComponentModel:
    """Load the flixopt component section from the example config file."""
    config_path = example_dir / "02_config_example.json"
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_component = raw_config["controller_components"][0]
    return ControllerComponentModel.model_validate(raw_component)


def _load_static_entities(example_dir: Path) -> list[StaticDataEntityModel]:
    """Load static input values from the example static data file."""
    static_data_path = example_dir / "static_data_flixopt.json"
    raw_static = json.loads(static_data_path.read_text(encoding="utf-8"))
    storage_level = raw_static["staticdata"][0]["attributes"][0]["value"]

    return [
        StaticDataEntityModel(
            id="flixopt_input_test",
            attributes=[
                InputDataAttributeModel(
                    id="storage_level",
                    data=float(storage_level),
                    data_type=AttributeTypes.VALUE,
                    data_available=True,
                    latest_timestamp_input=pd.Timestamp("2026-01-01T00:00:00Z"),
                )
            ],
        )
    ]


def _load_input_entity(example_dir: Path) -> InputDataEntityModel:
    """Load the three required timeseries inputs from the example CSV file."""
    input_path = example_dir / "inputs_flixopt.csv"
    data = pd.read_csv(input_path, sep=";", decimal=",")
    data["Time"] = pd.to_datetime(data["Time"], utc=True)
    data.set_index("Time", inplace=True)

    attributes = [
        InputDataAttributeModel(
            id="electricity_demand",
            data=data[["flixopt_input_entity.electricity_demand"]],
            data_type=AttributeTypes.TIMESERIES,
            data_available=True,
            latest_timestamp_input=data.index[0].to_pydatetime(),
        ),
        InputDataAttributeModel(
            id="heat_demand",
            data=data[["flixopt_input_entity.heat_demand"]],
            data_type=AttributeTypes.TIMESERIES,
            data_available=True,
            latest_timestamp_input=data.index[0].to_pydatetime(),
        ),
        InputDataAttributeModel(
            id="electricity_price",
            data=data[["flixopt_input_entity.electricity_price"]],
            data_type=AttributeTypes.TIMESERIES,
            data_available=True,
            latest_timestamp_input=data.index[0].to_pydatetime(),
        ),
    ]

    return InputDataEntityModel(id="flixopt_input_entity", attributes=attributes)


@pytest.mark.integration
def test_example_config_smoke_runs_flixopt_component(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the real flixopt example configuration once on component level."""
    if not _highs_solver_available():
        pytest.skip("Optional dependency highspy is not installed.")

    example_dir = _example_dir()
    monkeypatch.chdir(example_dir)

    component = FlixoptModelComponent(
        config=_load_component_config(example_dir),
        component_id="flixopt_model_component",
        static_data=_load_static_entities(example_dir),
    )

    input_model = InputDataModel(
        input_entities=[_load_input_entity(example_dir)],
        output_entities=[],
        static_entities=_load_static_entities(example_dir),
    )

    component.set_input_data(input_model)
    component.calculate()

    assert hasattr(component, "output_data")

    output_data: Any = component.output_data
    assert getattr(output_data, "boiler_thermal_power").value.notna().all()
    assert getattr(output_data, "chp_thermal_power").value.notna().all()
    assert getattr(output_data, "chp_electrical_power").value.notna().all()
    assert getattr(output_data, "thermal_storage_soc").value.notna().all()
