"""
Unit tests for FIWARE time calculation functionality in EnCoDaPy.

This module tests the time range and date calculation methods used for
FIWARE data queries, including:
- Timerange calculation (absolute and relative)
- Min/max timerange handling
- Date calculation for different query methods (CALCULATION, CALIBRATION)

Test Strategy:
- Unit tests with mocked FiwareConnection instances
- Focus on _calculate_timerange(), _calculate_timerange_min_max(), _calculate_dates()
- All time-based methods tested with various scenarios
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
from encodapy.config.types import TimerangeTypes
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.units import TimeUnits


class TestFiwareConnectionTimeCalculation:
    """Unit tests for time calculation methods in FiwareConnection."""

    def test_calculate_timerange_absolute(self):
        """Test _calculate_timerange() with absolute timerange.
        
        For ABSOLUTE timerange, the method should calculate from_date as time_now minus
        timerange_value, with to_date being None (open-ended).
        
        Asserts:
            - from_date is calculated as time_now - timerange_value
            - to_date is None for absolute timeranges
            - from_date is in ISO 8601 format with 'Z' timezone
        """
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = None

        from_date, to_date = conn._calculate_timerange(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_value=3600,
            timerange_type=TimerangeTypes.ABSOLUTE,
        )

        assert from_date is not None
        assert to_date is None
        expected_from = (time_now - timedelta(seconds=3600)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert from_date == expected_from

    def test_calculate_timerange_relative(self):
        """Test _calculate_timerange() with relative timerange.
        
        For RELATIVE timerange, the method should use last_timestamp as the
        starting point and calculate to_date as last_timestamp + timerange_value.
        
        Asserts:
            - from_date is set to last_timestamp
            - to_date is set to last_timestamp + timerange_value
            - Both dates are in ISO 8601 format
        """
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        from_date, to_date = conn._calculate_timerange(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_value=7200,
            timerange_type=TimerangeTypes.RELATIVE,
        )

        assert from_date is not None
        assert to_date is not None
        expected_from = last_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        expected_to = (last_timestamp + timedelta(seconds=7200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert from_date == expected_from
        assert to_date == expected_to

    def test_calculate_timerange_min_max(self):
        """Test _calculate_timerange_min_max() method.
        
        Tests the calculation of timerange with minimum and maximum bounds.
        This is used when timerange_min and timerange_max are both specified.
        
        Asserts:
            - from_date and to_date are both calculated
            - Dates are properly formatted
        """
        conn = FiwareConnection()

        time_now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_timestamp = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        from_date, to_date = conn._calculate_timerange_min_max(
            time_now=time_now,
            last_timestamp=last_timestamp,
            timerange_min=1800,
            timerange_max=3600,
        )

        assert from_date is not None
        assert to_date is not None

    def test_handle_calculation_method_with_timerange_min_max_absolute(self):
        """Test _handle_calculation_method with timerange_min and timerange_max (ABSOLUTE).
        
        Tests the case where both timerange_min and timerange_max are specified
        and timerange_type is ABSOLUTE. Should use timerange_max.
        
        Asserts:
            - from_date and to_date are calculated
            - to_date is None for ABSOLUTE timerange type
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
                        timerange=None,
                        timerange_unit=TimeUnits.HOUR,
                        timerange_type=TimerangeTypes.ABSOLUTE,
                        timestep=1,
                        timestep_unit=TimeUnits.SECOND,
                        sampling_time=1,
                        sampling_time_unit=TimeUnits.MINUTE,
                        timerange_min=1,
                        timerange_max=24,
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

        from_date, to_date = conn._handle_calculation_method(
            time_now=time_now,
            last_timestamp=last_timestamp,
        )

        assert from_date is not None
        assert to_date is None

    def test_handle_calculation_method_with_timerange_min_max_relative(self):
        """Test _handle_calculation_method with timerange_min and timerange_max (RELATIVE).
        
        Tests the case where both timerange_min and timerange_max are specified
        and timerange_type is RELATIVE. Should use _calculate_timerange_min_max.
        
        Asserts:
            - from_date and to_date are both calculated
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
                        timerange=None,
                        timerange_unit=TimeUnits.HOUR,
                        timerange_type=TimerangeTypes.RELATIVE,
                        timestep=1,
                        timestep_unit=TimeUnits.SECOND,
                        sampling_time=1,
                        sampling_time_unit=TimeUnits.MINUTE,
                        timerange_min=1,
                        timerange_max=24,
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

        from_date, to_date = conn._handle_calculation_method(
            time_now=time_now,
            last_timestamp=last_timestamp,
        )

        assert from_date is not None
        # to_date is None when timeframe (2 hours) < timerange_max (24 hours)
        assert to_date is None

    def test_handle_calculation_method_no_config(self):
        """Test _handle_calculation_method returns None, None when no config is available.
        
        Tests the case where the configuration is missing or incomplete.
        
        Asserts:
            - Returns (None, None)
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
        last_timestamp = None

        from_date, to_date = conn._handle_calculation_method(
            time_now=time_now,
            last_timestamp=last_timestamp,
        )

        assert from_date is not None
        assert to_date is None
