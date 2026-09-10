"""
Shared fixtures for FIWARE unit tests.

This module provides common fixtures used across multiple FIWARE-related unit test files.
Fixtures here are designed for isolated unit testing with mocked dependencies.
"""

# pylint: disable=redefined-outer-name
import pytest

from encodapy.config import (
    ConfigModel,
    ControllerSettingModel,
    InterfaceModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsModel,
    TimeSettingsResultsModel,
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
        controller_settings=ControllerSettingModel(
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
                results=TimeSettingsResultsModel(
                    timerange=1,
                    timerange_unit=TimeUnits.HOUR,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                ),
            ),
            specific_settings={},
        ),
    )


@pytest.fixture
def mock_controller_settings() -> ControllerSettingModel:
    """Create a minimal ControllerSettingModel for unit testing.
    
    This fixture provides just the controller settings part for tests
    that need to set conn.controller_settings directly.
    
    Returns:
        ControllerSettingModel: Configuration with time settings.
    """
    return ControllerSettingModel(
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
            results=TimeSettingsResultsModel(
                timerange=1,
                timerange_unit=TimeUnits.HOUR,
                timestep=1,
                timestep_unit=TimeUnits.SECOND,
                sampling_time=1,
                sampling_time_unit=TimeUnits.MINUTE,
            ),
        ),
        specific_settings={},
    )
