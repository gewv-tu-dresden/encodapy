"""Unit tests for the ThermalStorage component (encodapy.components.thermal_storage).

The tests cover the volume calculation per sensor, the energy content
calculation for all energy types, the state of charge calculation and the
temperature based level check.
"""

# pylint: disable=protected-access
from __future__ import annotations

import math
from typing import cast

import pandas as pd
import pytest

from encodapy.components.basic_component_config import ComponentValidationError
from encodapy.components.thermal_storage.thermal_storage_config import (
    ThermalStorageCalculationMethods,
    ThermalStorageEnergyTypes,
)
from encodapy.utils.units import DataUnits

from . import helpers

TEMPERATURES = [80.0, 60.0, 50.0]
HEIGHTS = [10.0, 50.0, 90.0]


class TestVolumeCalculation:
    """Tests for the volume calculation per sensor."""

    def test_volume_per_sensor(self) -> None:
        """The volume is split at the midpoints between the sensor heights."""
        component = helpers.make_component(temperatures=TEMPERATURES, heights=HEIGHTS)

        assert component.sensor_volumes == {0: 3.0, 1: 4.0, 2: 3.0}

    def test_sensor_volumes_sum_up_to_total_volume(self) -> None:
        """The sum of all sensor volumes equals the configured volume."""
        component = helpers.make_component(
            temperatures=TEMPERATURES, heights=[5.0, 55.0, 95.0]
        )

        assert component.sensor_volumes is not None
        assert math.isclose(sum(component.sensor_volumes.values()), helpers.VOLUME)

    def test_get_sensor_volume_is_rounded(self) -> None:
        """The returned sensor volume is rounded to three decimals."""
        component = helpers.make_component(
            temperatures=TEMPERATURES, heights=[10.0, 50.0, 91.0]
        )

        assert component.sensor_volumes is not None
        volume = component._get_sensor_volume(sensor=1)

        assert volume == round(component.sensor_volumes[1], 3)

    def test_get_sensor_volume_without_volumes_raises(self) -> None:
        """A missing volume calculation raises a ValueError."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        component.sensor_volumes = None

        with pytest.raises(ValueError, match="Sensor volumes are not set"):
            component._get_sensor_volume(sensor=0)

    def test_get_sensor_volume_of_unknown_sensor_raises(self) -> None:
        """An unconfigured sensor raises a ValueError."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        with pytest.raises(ValueError, match="Sensor 3 is not configured"):
            component._get_sensor_volume(sensor=3)


class TestSensorValues:
    """Tests for the access to the storage temperature sensor values."""

    def test_get_temperature_sensor_value(self) -> None:
        """The temperature of a configured sensor is returned as DataPointNumber."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        temperature = component.get_storage_temperature_sensor_value(sensor_index=0)

        assert temperature.value == 80.0
        assert temperature.unit is DataUnits.DEGREECELSIUS

    def test_get_temperature_sensor_value_of_unknown_sensor_raises(self) -> None:
        """A sensor above the maximum sensor count raises an AttributeError."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        with pytest.raises(AttributeError, match="not found in input data"):
            component.get_storage_temperature_sensor_value(sensor_index=10)

    def test_get_temperature_sensor_value_of_unset_sensor_raises(self) -> None:
        """A configured but unset sensor raises a ValueError."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        with pytest.raises(ValueError, match="is not set"):
            component.get_storage_temperature_sensor_value(sensor_index=3)


class TestEnergyContent:
    """Tests for the energy content calculation for all energy types."""

    def test_nominal_energy(self) -> None:
        """The nominal energy is based on the configured temperature limits."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        energy = component.get_storage_energy_content(ThermalStorageEnergyTypes.NOMINAL)

        assert energy == helpers.expected_energy(
            temperature_differences=[50.0, 50.0, 50.0],
            volumes=helpers.nominal_volumes(HEIGHTS),
            temperatures=TEMPERATURES,
        )

    def test_nominal_energy_as_datapoint(self) -> None:
        """The nominal energy is returned as DataPointNumber in Wh."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage_energy_nominal()

        assert datapoint.unit is DataUnits.WHR
        assert datapoint.value == component.get_storage_energy_content(
            ThermalStorageEnergyTypes.NOMINAL
        )

    def test_minimal_energy_with_reference_temperature(self) -> None:
        """The minimal energy is the energy at the minimal temperature limit."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        energy = component.get_storage_energy_content(ThermalStorageEnergyTypes.MINIMAL)

        assert energy == helpers.expected_energy(
            temperature_differences=[0.0, 0.0, 0.0],
            volumes=helpers.nominal_volumes(HEIGHTS),
            temperatures=TEMPERATURES,
        )

    def test_minimal_energy_as_datapoint(self) -> None:
        """The minimal energy is returned as DataPointNumber in Wh."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage_energy_minimum()

        assert datapoint.unit is DataUnits.WHR
        assert datapoint.value == 0.0

    def test_maximal_energy(self) -> None:
        """The maximal energy is the energy at the maximal temperature limit."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        energy = component.get_storage_energy_content(ThermalStorageEnergyTypes.MAXIMAL)

        assert energy == helpers.expected_energy(
            temperature_differences=[50.0, 50.0, 50.0],
            volumes=helpers.nominal_volumes(HEIGHTS),
            temperatures=TEMPERATURES,
        )

    def test_maximal_energy_as_datapoint(self) -> None:
        """The maximal energy is returned as DataPointNumber in Wh."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage_energy_maximum()

        assert datapoint.unit is DataUnits.WHR
        assert datapoint.value == component.get_storage_energy_content(
            ThermalStorageEnergyTypes.MAXIMAL
        )

    def test_current_energy(self) -> None:
        """The current energy is based on the measured temperatures."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        energy = component.get_storage_energy_content(ThermalStorageEnergyTypes.CURRENT)

        assert energy == helpers.expected_energy(
            temperature_differences=[40.0, 20.0, 10.0],
            volumes=helpers.nominal_volumes(HEIGHTS),
            temperatures=TEMPERATURES,
        )

    def test_unknown_energy_type_raises(self) -> None:
        """An unknown energy type raises a ValueError."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        with pytest.raises(ValueError, match="Unknown energy type"):
            component.get_storage_energy_content(
                cast(ThermalStorageEnergyTypes, "unknown")
            )

    def test_energy_content_without_volumes_raises(self) -> None:
        """The energy calculation requires prepared sensor volumes."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        component.sensor_volumes = None

        with pytest.raises(ValueError, match="Sensor volumes are not set"):
            component.get_storage_energy_content(ThermalStorageEnergyTypes.NOMINAL)

    def test_mean_maximal_temperature(self) -> None:
        """The mean maximal temperature is weighted with the sensor volumes."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage__mean_temperature_maximal()

        assert datapoint.value == 90.0
        assert datapoint.unit is DataUnits.DEGREECELSIUS


class TestStateOfCharge:
    """Tests for the state of charge calculation."""

    def test_state_of_charge(self) -> None:
        """The state of charge is the current energy relative to the nominal energy."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        state_of_charge = component.get_state_of_charge()

        nominal = component.get_storage_energy_content(
            ThermalStorageEnergyTypes.NOMINAL
        )
        current = component.get_storage_energy_content(
            ThermalStorageEnergyTypes.CURRENT
        )
        assert state_of_charge.value == round(current / nominal * 100, 2)
        assert state_of_charge.unit is DataUnits.PERCENT

    def test_state_of_charge_is_cached(self) -> None:
        """The state of charge is only recalculated after the check interval."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        first_call = component.get_state_of_charge()
        cached_call = component.get_state_of_charge()

        assert first_call.value == cached_call.value
        assert component.state_of_charge_information.check_status is True

    def test_state_of_charge_limited_to_bounds(self) -> None:
        """The state of charge is limited to the range 0 to 100 percent."""
        component = helpers.make_component(temperatures=[95.0, 95.0, 95.0])

        state_of_charge = component.get_state_of_charge()

        assert state_of_charge.value == 100.0

    def test_current_energy_uses_state_of_charge(self) -> None:
        """The current energy is derived from the state of charge."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage_energy_current()
        state_of_charge = component.state_of_charge_information.state_of_charge
        nominal_energy = component.state_of_charge_information.nominal_storage_energy
        assert state_of_charge is not None and nominal_energy is not None

        assert datapoint.unit is DataUnits.WHR
        assert datapoint.value == round(
            state_of_charge / 100 * nominal_energy,
            2,
        )

    def test_loading_potential_is_difference_to_nominal_energy(self) -> None:
        """The loading potential is the nominal energy minus the current energy."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        datapoint = component.get_storage_loading_potential_nominal()

        assert datapoint.unit is DataUnits.WHR
        assert datapoint.value == round(
            component.get_storage_energy_content(ThermalStorageEnergyTypes.NOMINAL)
            - component.get_storage_energy_current().value,
            2,
        )


class TestStateOfChargeAdjustment:
    """Tests for the temperature based adjustment of the state of charge."""

    def test_adjust_state_of_charge_with_nan_factor(self) -> None:
        """A NaN factor keeps the state of charge unchanged."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_level_check={"enabled": True},
        )

        adjusted = component._adjust_state_of_charge(
            state_of_charge=55.0, mean_current_factor=float("nan")
        )

        assert adjusted == 55.0

    def test_adjust_state_of_charge_with_negative_factor(self) -> None:
        """A negative factor means there is no usable energy left."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_level_check={"enabled": True},
        )

        adjusted = component._adjust_state_of_charge(
            state_of_charge=55.0, mean_current_factor=-0.5
        )

        assert adjusted == 0.0

    def test_adjust_state_of_charge_with_factor_above_one(self) -> None:
        """A factor above one keeps the state of charge unchanged."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_level_check={"enabled": True},
        )

        adjusted = component._adjust_state_of_charge(
            state_of_charge=55.0, mean_current_factor=1.5
        )

        assert adjusted == 55.0

    def test_adjust_state_of_charge_with_partial_factor(self) -> None:
        """A factor between zero and one reduces the state of charge linearly."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_level_check={"enabled": True},
        )

        adjusted = component._adjust_state_of_charge(
            state_of_charge=50.0, mean_current_factor=0.5
        )

        assert adjusted == 25.0

    def test_check_disabled_returns_state_of_charge(self) -> None:
        """A disabled level check returns the state of charge unchanged."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_level_check={"enabled": False},
        )

        checked = component._check_temperature_of_required_sensors(state_of_charge=42.0)

        assert checked == 42.0

    def test_top_sensor_below_minimum_results_in_zero(self) -> None:
        """A top sensor below the minimal temperature means no usable energy."""
        component = helpers.make_component(
            temperatures=[30.0, 60.0, 50.0],
            load_level_check={"enabled": True, "minimal_level": 35.0},
        )

        checked = component._check_temperature_of_required_sensors(state_of_charge=42.0)

        assert checked == 0.0

    def test_all_sensors_above_reference_keep_state_of_charge(self) -> None:
        """Temperatures above the reference temperature keep the state of charge."""
        component = helpers.make_component(
            temperatures=[80.0, 80.0, 80.0],
            load_level_check={"enabled": True, "minimal_level": 35.0},
        )

        checked = component._check_temperature_of_required_sensors(state_of_charge=42.0)

        assert checked == 42.0

    def test_sensor_with_equal_limits_is_skipped(self) -> None:
        """A sensor with equal temperature limits does not break the check."""
        sensor_config = {
            "storage_sensors": [
                {
                    "height": 10.0,
                    "limits": {
                        "minimal_temperature": 40.0,
                        "maximal_temperature": 40.0,
                        "reference_temperature": 40.0,
                    },
                },
                {
                    "height": 50.0,
                    "limits": dict(helpers.SENSOR_LIMITS),
                },
                {
                    "height": 90.0,
                    "limits": dict(helpers.SENSOR_LIMITS),
                },
            ]
        }
        component = helpers.make_component(
            temperatures=[45.0, 80.0, 80.0],
            load_level_check={"enabled": True, "minimal_level": 35.0},
            config_overrides={"sensor_config": {"value": sensor_config}},
        )

        checked = component._check_temperature_of_required_sensors(state_of_charge=42.0)

        assert checked >= 0.0


class TestCalculationMethods:
    """Tests for the calculation method dependent sensor limits."""

    def test_static_limits_are_used(self) -> None:
        """The static calculation method returns the configured limits."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            calculation_method=(ThermalStorageCalculationMethods.STATIC_LIMITS.value),
        )

        limits = component._get_sensor_limits(sensor_id=0)

        assert limits.minimal_temperature == 40.0
        assert limits.maximal_temperature == 90.0

    def test_connection_limits_use_outflow_for_top_sensor(self) -> None:
        """The top sensor uses the outflow temperature as minimal limit."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            calculation_method=(
                ThermalStorageCalculationMethods.CONNECTION_LIMITS.value
            ),
            load_temperatures=(45.0, 55.0),
        )

        limits = component._get_sensor_limits(sensor_id=0)

        assert limits.minimal_temperature == 55.0
        assert limits.maximal_temperature == 90.0

    def test_connection_limits_use_inflow_for_lower_sensors(self) -> None:
        """All sensors below the top use the inflow temperature as minimal limit."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            calculation_method=(
                ThermalStorageCalculationMethods.CONNECTION_LIMITS.value
            ),
            load_temperatures=(45.0, 55.0),
        )

        limits = component._get_sensor_limits(sensor_id=1)

        assert limits.minimal_temperature == 45.0

    def test_connection_limits_fall_back_to_config_limits(self) -> None:
        """Missing load temperatures fall back to the configured limits."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_temperatures=(45.0, 55.0),
        )
        component.input_data.load_temperature_out = None
        component.config_data.calculation_method.value = (
            ThermalStorageCalculationMethods.CONNECTION_LIMITS
        )

        limits = component._get_sensor_limits(sensor_id=0)

        assert limits.minimal_temperature == 40.0

    def test_connection_limits_fall_back_when_inflow_is_missing(self) -> None:
        """A missing inflow temperature falls back to the configured limits."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            load_temperatures=(45.0, 55.0),
        )
        component.input_data.load_temperature_in = None
        component.config_data.calculation_method.value = (
            ThermalStorageCalculationMethods.CONNECTION_LIMITS
        )

        limits = component._get_sensor_limits(sensor_id=1)

        assert limits.minimal_temperature == 40.0

    def test_historical_limits_use_config_limits(self) -> None:
        """The historical limits method uses the configured limits."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            calculation_method=(
                ThermalStorageCalculationMethods.HISTORICAL_LIMITS.value
            ),
        )

        limits = component._get_sensor_limits(sensor_id=0)

        assert limits.minimal_temperature == 40.0
        assert limits.maximal_temperature == 90.0

    def test_unknown_calculation_method_falls_back_to_config_limits(self) -> None:
        """An unknown calculation method falls back to the configured limits."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        component.config_data.calculation_method.value = cast(
            ThermalStorageCalculationMethods, "unknown_method"
        )

        limits = component._get_sensor_limits(sensor_id=0)

        assert limits.minimal_temperature == 40.0

    def test_set_input_data_with_connection_limits_requires_sensors(self) -> None:
        """The connection limits method requires the load connection sensors."""
        with pytest.raises(ComponentValidationError, match="not configured"):
            helpers.make_component(
                temperatures=TEMPERATURES,
                calculation_method=(
                    ThermalStorageCalculationMethods.CONNECTION_LIMITS.value
                ),
            )


class TestPreparation:
    """Tests for the preparation of the component."""

    def test_component_is_prepared_during_initialization(self) -> None:
        """The sensor volumes are calculated during initialization."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        assert component.sensor_volumes is not None

    def test_prepare_component_recalculates_volumes(self) -> None:
        """The preparation calculates the sensor volumes."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        component.sensor_volumes = None

        component.prepare_component()

        assert component.sensor_volumes == {0: 3.0, 1: 4.0, 2: 3.0}

    def test_input_configuration_must_match_sensor_configuration(self) -> None:
        """A mismatch between inputs and sensors raises a validation error."""
        with pytest.raises(ComponentValidationError, match="does not match"):
            helpers.make_component(temperatures=[80.0, 60.0, 50.0, 45.0])

    def test_missing_io_model_raises_key_error(self) -> None:
        """A missing I/O model raises a KeyError."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        component.io_model = None

        with pytest.raises(KeyError, match="No I/O model"):
            component.prepare_component()


class TestCalculation:
    """Tests for the full calculation of the component."""

    def test_calculate_sets_all_outputs(self) -> None:
        """The calculation fills all output datapoints."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        component.calculate()

        assert component.output_data.storage__level is not None
        assert component.output_data.storage__energy is not None
        assert component.output_data.storage__energy_nominal is not None
        assert component.output_data.storage__loading_potential_nominal is not None

    def test_calculated_values_are_consistent(self) -> None:
        """The calculated level and energies are consistent with each other."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        component.calculate()

        level = component.output_data.storage__level
        loading_potential = component.output_data.storage__loading_potential_nominal
        nominal_energy = component.output_data.storage__energy_nominal
        current_energy = component.output_data.storage__energy
        assert (
            level is not None
            and loading_potential is not None
            and nominal_energy is not None
            and current_energy is not None
        )

        assert 0.0 <= level.value <= 100.0
        assert loading_potential.value == round(
            nominal_energy.value - current_energy.value,
            2,
        )


class TestTemperatureHistory:
    """Tests for storing and handling the temperature history."""

    def test_store_temperature_history(self) -> None:
        """The temperatures are stored as a pandas Series per sensor."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        component.store_storage_temperature_history()

        assert set(component.sensor_values_stored) == {0, 1, 2}
        for index, series in component.sensor_values_stored.items():
            assert isinstance(series, pd.Series)
            assert series.loc[helpers.STORAGE_TIME] == TEMPERATURES[index]

    def test_store_temperature_history_grows(self) -> None:
        """Repeated calls append new temperatures to the history."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        component.store_storage_temperature_history()
        component.set_input_data(
            helpers.input_data(
                temperatures=TEMPERATURES,
                time=helpers.STORAGE_TIME.replace(minute=10),
            )
        )
        component.store_storage_temperature_history()

        assert len(component.sensor_values_stored[0]) == 2

    def test_handle_historical_data_without_history(self) -> None:
        """Without any history no extrema are returned."""
        component = helpers.make_component(temperatures=TEMPERATURES)

        assert component.handle_storage_sensor_historical_data(0) is None

    def test_handle_historical_data_returns_extrema(self) -> None:
        """A history covering the minimum time range returns the extrema."""
        component = helpers.make_component(
            temperatures=TEMPERATURES,
            config_overrides={
                "calibration": {
                    "value": {"db_path": None, "historical_timerange_minimum": 1}
                }
            },
        )
        component.store_storage_temperature_history()
        later = helpers.STORAGE_TIME.replace(hour=14)
        component.set_input_data(
            helpers.input_data(
                temperatures=[60.0, 55.0, 45.0],
                time=later,
            )
        )
        component.store_storage_temperature_history()

        extrema = component.handle_storage_sensor_historical_data(0)

        assert extrema is not None
        assert extrema.minimal_temperature == 60.0
        assert extrema.maximal_temperature == 80.0

    def test_calibrate_without_historical_method_does_nothing(self) -> None:
        """The calibration is skipped for non historical calculation methods."""
        component = helpers.make_component(temperatures=TEMPERATURES)
        limits_before = [
            sensor.limits.model_dump()
            for sensor in component.config_data.sensor_config.value.storage_sensors
        ]

        component.calibrate()

        limits_after = [
            sensor.limits.model_dump()
            for sensor in component.config_data.sensor_config.value.storage_sensors
        ]
        assert limits_before == limits_after
