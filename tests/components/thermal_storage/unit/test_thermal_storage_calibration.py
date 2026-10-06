"""Unit tests for the calibration of the ThermalStorage component.

The calibration uses historical temperature data to adjust the sensor
limits. The calibration database is written to a temporary sqlite file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from encodapy.components.thermal_storage.calibration_data import CalibrationData
from encodapy.components.thermal_storage.thermal_storage import ThermalStorage
from encodapy.components.thermal_storage.thermal_storage_config import (
    ThermalStorageCalculationMethods,
)

from . import helpers

TEMPERATURES = [80.0, 60.0, 50.0]
LATER_TEMPERATURES = [70.0, 55.0, 45.0]


def calibration_config(db_path: str | None) -> dict[str, dict]:
    """Create a calibration config override with the given database path."""
    return {"calibration": {"value": {"db_path": db_path}}}


def fill_history(
    component: ThermalStorage,
    later_temperatures: list[float] | None = None,
) -> None:
    """Store a first and a second (two hours later) measurement in the history."""
    component.store_storage_temperature_history()
    component.set_input_data(
        helpers.input_data(
            temperatures=later_temperatures or LATER_TEMPERATURES,
            time=helpers.STORAGE_TIME.replace(hour=14),
        )
    )
    component.store_storage_temperature_history()


def expected_adjusted_limit(historical_value: float, config_value: float) -> float:
    """Expected adjusted limit with the default margin of five percent."""
    return round((historical_value * 0.95 + config_value) / 2, 1)


def expected_adjusted_maximum(historical_value: float, config_value: float) -> float:
    """Expected adjusted maximum limit with the default margin of five percent."""
    return round((historical_value * 1.05 + config_value) / 2, 1)


class TestHistoricalCalibration:
    """Tests for the history based calibration of the sensor limits."""

    def test_calibration_adjusts_unprotected_limits(self) -> None:
        """Unprotected limits are adjusted based on the historical extrema."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides=calibration_config(None),
        )
        fill_history(component)

        component.calibrate_historical_based_sensor_configuration()

        sensor = component.config_data.sensor_config.value.storage_sensors[0]
        assert sensor.limits.minimal_temperature == expected_adjusted_limit(70.0, 40.0)
        assert sensor.limits.maximal_temperature == expected_adjusted_maximum(
            80.0, 90.0
        )

    def test_calibration_keeps_protected_limits(self) -> None:
        """Protected limits are not adjusted during the calibration."""
        sensors = helpers.sensor_config([10.0, 50.0, 90.0])["storage_sensors"]
        sensors[1]["protected_upper_limit"] = True
        sensors[1]["protected_lower_limit"] = True
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides={
                "sensor_config": {"value": {"storage_sensors": sensors}},
                **calibration_config(None),
            },
        )
        fill_history(component)

        component.calibrate_historical_based_sensor_configuration()

        sensor = component.config_data.sensor_config.value.storage_sensors[1]
        assert sensor.limits.minimal_temperature == 40.0
        assert sensor.limits.maximal_temperature == 90.0

    def test_calibration_without_history_keeps_limits(self) -> None:
        """Without any historical data the limits are not adjusted."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides=calibration_config(None),
        )

        component.calibrate_historical_based_sensor_configuration()

        for sensor in component.config_data.sensor_config.value.storage_sensors:
            assert sensor.limits.minimal_temperature == 40.0
            assert sensor.limits.maximal_temperature == 90.0

    def test_calibrate_with_historical_method_adjusts_limits(self) -> None:
        """The calibration runs for the historical limits calculation method."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            calculation_method=ThermalStorageCalculationMethods.HISTORICAL_LIMITS.value,
            config_overrides=calibration_config(None),
        )
        fill_history(component)

        component.calibrate()

        sensor = component.config_data.sensor_config.value.storage_sensors[0]
        assert sensor.limits.minimal_temperature == expected_adjusted_limit(70.0, 40.0)


class TestCalibrationDatabase:
    """Tests for the persistence of the calibration data in sqlite."""

    def test_extrema_are_stored_in_database(self, tmp_path: Path) -> None:
        """The extrema of a sensor are stored in the calibration database."""
        db_path = str(tmp_path / "calibration")
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides=calibration_config(db_path),
        )
        fill_history(component)

        extrema = component.handle_storage_sensor_historical_data(0)

        assert extrema is not None
        assert component.calibration_data is not None
        stored = component.calibration_data.load_extrema_sqlite(sensor_index=0)
        assert stored is not None
        assert stored.minimal_temperature == extrema.minimal_temperature
        assert stored.maximal_temperature == extrema.maximal_temperature

    def test_extrema_are_merged_with_stored_extrema(self, tmp_path: Path) -> None:
        """New extrema are merged with the extrema from the database."""
        db_path = str(tmp_path / "calibration")
        first_component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides=calibration_config(db_path),
        )
        fill_history(first_component)
        first_component.handle_storage_sensor_historical_data(0)

        second_component = helpers.make_component(
            temperatures=[65.0, 55.0, 45.0],
            config_overrides=calibration_config(db_path),
        )
        second_component.set_input_data(
            helpers.input_data(
                temperatures=[65.0, 55.0, 45.0],
                time=helpers.STORAGE_TIME.replace(hour=15),
            )
        )
        second_component.store_storage_temperature_history()
        second_component.set_input_data(
            helpers.input_data(
                temperatures=[75.0, 60.0, 50.0],
                time=helpers.STORAGE_TIME.replace(hour=16),
            )
        )
        second_component.store_storage_temperature_history()

        extrema = second_component.handle_storage_sensor_historical_data(0)

        assert extrema is not None
        assert extrema.minimal_temperature == 65.0
        assert extrema.maximal_temperature == 80.0

    def test_limits_are_stored_in_database(self, tmp_path: Path) -> None:
        """The calibrated limits persist in the calibration database."""
        db_path = str(tmp_path / "calibration")
        first_component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides=calibration_config(db_path),
        )
        fill_history(first_component)
        first_component.calibrate_historical_based_sensor_configuration()

        database = CalibrationData(db_path=db_path)
        loaded = database.load_limits_sqlite(
            sensor_config=first_component.config_data.sensor_config.value
        )

        calibrated = first_component.config_data.sensor_config.value.storage_sensors
        for original, sensor in zip(calibrated, loaded.storage_sensors, strict=True):
            assert sensor.limits.minimal_temperature == pytest.approx(
                original.limits.minimal_temperature
            )
            assert sensor.limits.maximal_temperature == pytest.approx(
                original.limits.maximal_temperature
            )
