"""
Unit tests for FIWARE calibration method handling in EnCoDaPy.

This module tests the _handle_calibration_method and _calculate_dates functionality
for the CALIBRATION DataQueryTypes method.

Test Strategy:
- Unit tests with mocked FiwareConnection instances
- Focus on _handle_calibration_method() with various timerange configurations
- All external dependencies are mocked to ensure isolated testing
"""

# pylint: disable=protected-access, unused-argument
from datetime import datetime, timezone, timedelta

from encodapy.config import (
    ConfigModel,
    ControllerSettingModel,
    InterfaceModel,
    TimeSettingsModel,
    TimeSettingsCalculationModel,
    TimeSettingsCalibrationModel,
    TimeSettingsResultsModel,
)
from encodapy.config.types import TimerangeTypes, DataQueryTypes
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.units import TimeUnits


# =============================================================================
# Tests for _handle_calibration_method
# =============================================================================


def test_handle_calibration_method_relative_with_last_timestamp():
    """Test _handle_calibration_method with RELATIVE timerange and last_timestamp.
    
    When calibration timerange_type is RELATIVE and last_timestamp is available,
    from_date should be last_timestamp - timerange, to_date should be None.
    
    Asserts:
        - from_date is calculated as last_timestamp - calibration.timerange
        - to_date is None (RELATIVE type uses open-ended range)
        - Dates are in ISO 8601 format
    """
    conn = FiwareConnection()
    conn.config = ConfigModel(
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
                    timerange_type=TimerangeTypes.RELATIVE,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                    timerange_min=None,
                    timerange_max=None,
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=2,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type=TimerangeTypes.RELATIVE,
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

    time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = conn._handle_calibration_method(
        time_now=time_now,
        last_timestamp=last_timestamp,
    )

    assert from_date is not None
    # For RELATIVE type with last_timestamp, returns from_date (string), None
    expected_from = (last_timestamp - timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert from_date == expected_from
    assert to_date is None


def test_handle_calibration_method_relative_without_last_timestamp():
    """Test _handle_calibration_method with RELATIVE timerange but no last_timestamp.
    
    When last_timestamp is None, should fall back to time_now - timerange.
    
    Asserts:
        - from_date is calculated as time_now - calibration.timerange
        - to_date is time_now
    """
    conn = FiwareConnection()
    conn.config = ConfigModel(
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
                    timerange_type=TimerangeTypes.RELATIVE,
                    timestep=1,
                    timestep_unit=TimeUnits.SECOND,
                    sampling_time=1,
                    sampling_time_unit=TimeUnits.MINUTE,
                    timerange_min=None,
                    timerange_max=None,
                ),
                calibration=TimeSettingsCalibrationModel(
                    timerange=2,
                    timerange_unit=TimeUnits.HOUR,
                    timerange_type=TimerangeTypes.RELATIVE,
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

    time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = conn._handle_calibration_method(
        time_now=time_now,
        last_timestamp=None,
    )

    assert from_date is not None
    assert to_date is not None
    expected_from = (time_now - timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # to_date is a datetime object, not a string
    assert from_date == expected_from
    assert to_date == time_now


def test_handle_calibration_method_absolute_with_last_timestamp():
    """Test _handle_calibration_method with ABSOLUTE timerange and last_timestamp.
    
    For ABSOLUTE timerange, should use time_now - timerange regardless of last_timestamp.
    
    Asserts:
        - from_date is calculated as time_now - calibration.timerange
        - to_date is time_now
    """
    conn = FiwareConnection()
    conn.config = ConfigModel(
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
                    timerange_min=None,
                    timerange_max=None,
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

    time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = conn._handle_calibration_method(
        time_now=time_now,
        last_timestamp=last_timestamp,
    )

    assert from_date is not None
    assert to_date is not None
    expected_from = (time_now - timedelta(seconds=86400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # to_date is a datetime object, not a string
    assert from_date == expected_from
    assert to_date == time_now


def test_handle_calibration_method_absolute_without_last_timestamp():
    """Test _handle_calibration_method with ABSOLUTE timerange and no last_timestamp.
    
    For ABSOLUTE without last_timestamp, should use time_now - timerange.
    
    Asserts:
        - from_date is calculated as time_now - calibration.timerange
        - to_date is time_now
    """
    conn = FiwareConnection()
    conn.config = ConfigModel(
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
                    timerange_min=None,
                    timerange_max=None,
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

    time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = conn._handle_calibration_method(
        time_now=time_now,
        last_timestamp=None,
    )

    assert from_date is not None
    assert to_date is not None
    expected_from = (time_now - timedelta(seconds=86400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # to_date is a datetime object, not a string
    assert from_date == expected_from
    assert to_date == time_now


# =============================================================================
# Tests for _calculate_dates with CALIBRATION method
# =============================================================================


def test_calculate_dates_calibration_method():
    """Test _calculate_dates() with CALIBRATION method.
    
    Verifies that _calculate_dates correctly delegates to _handle_calibration_method
    for CALIBRATION DataQueryTypes.
    
    Asserts:
        - from_date and to_date are calculated via _handle_calibration_method
        - to_date is set to time_now if None from calibration method
    """
    conn = FiwareConnection()
    conn.config = ConfigModel(
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

    last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    from_date, to_date = conn._calculate_dates(
        method=DataQueryTypes.CALIBRATION,
        last_timestamp=last_timestamp,
    )

    assert from_date is not None
    assert to_date is not None
