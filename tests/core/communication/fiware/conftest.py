"""
Shared fixtures for FIWARE unit tests.

This module provides common fixtures used across multiple FIWARE-related unit test files.
Fixtures here are designed for isolated unit testing with mocked dependencies.
"""

# pylint: disable=redefined-outer-name
import pytest

from encodapy.config import (
    ConfigModel,
    InterfaceModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsModel,
)
from encodapy.config.types import TimerangeTypes
from encodapy.utils.units import TimeUnits


@pytest.fixture
def mock_config() -> ConfigModel:
    """Create a minimal ConfigModel instance for unit testing.

    Returns:
        ConfigModel: Minimal configuration with FIWARE interface enabled
            and default time settings for testing.
    """
    return ConfigModel(
        interfaces=InterfaceModel(fiware=True, file=False, mqtt=False),
        inputs=[],
        outputs=[],
        staticdata=[],
        controller_components=[],
        time_settings=TimeSettingsModel(
            calculation=TimeSettingsCalculationModel(
                timerange=24,
                timerange_unit=TimeUnits.HOUR,
                timerange_type=TimerangeTypes.ABSOLUTE,
                timestep=1,
                timestep_unit=TimeUnits.SECOND,
                sampling_time=1,
                sampling_time_unit=TimeUnits.MINUTE,
            ),
            calibration=TimeSettingsCalibrationModel(
                timerange=24,
                timerange_unit=TimeUnits.HOUR,
                timerange_type=TimerangeTypes.ABSOLUTE,
                timestep=1,
                timestep_unit=TimeUnits.SECOND,
                sampling_time=1,
                sampling_time_unit=TimeUnits.MINUTE,
            ),
        ),
    )
