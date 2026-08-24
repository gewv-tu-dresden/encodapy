"""
Tests for ControllerBasicService loop and timing functionality.

This module contains tests for the main service loops, timing, and health check
functionality of the ControllerBasicService class.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import TimeSettingsCalibrationModel, TimeSettingsModel, TimeSettingsCalculationModel
from encodapy.utils.units import TimeUnits


class TestHoldSamplingTime:
    """Test class for the _hold_sampling_time method."""

    @pytest.mark.asyncio
    async def test_hold_sampling_time_normal_wait(self, unset_shutdown_event):
        """
        Test normal waiting behavior until sampling time is reached.
        
        Verifies that the method waits for the specified hold_time when
        the elapsed time is less than the sampling time.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = 0.1  # 100ms
        
        await service._hold_sampling_time(start_time, hold_time)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed >= hold_time

    @pytest.mark.asyncio
    async def test_hold_sampling_time_exact_timing(self, unset_shutdown_event):
        """
        Test that the method waits at least the specified time.
        
        Verifies that the actual wait time is at least the specified
        hold_time, accounting for small measurement errors.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = 0.05  # 50ms - short enough for fast tests
        
        await service._hold_sampling_time(start_time, hold_time)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        # Allow small tolerance for timing
        assert elapsed >= hold_time * 0.9  # At least 90% of hold_time

    @pytest.mark.asyncio
    async def test_hold_sampling_time_already_exceeded(self, capsys, unset_shutdown_event):
        """
        Test that a warning is logged when processing time exceeds sampling time.
        
        Verifies that the method logs a warning when the elapsed time
        is already greater than the sampling time.
        
        Note: Uses loguru which logs to stdout, so we check captured stdout.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        # Simulate that processing already took longer than sampling time
        start_time = datetime.now() - timedelta(seconds=1)  # 1 second ago
        hold_time = 0.1  # Only 100ms
        
        # loguru logs to stdout, capsys captures it
        await service._hold_sampling_time(start_time, hold_time)
        
        # Check captured stdout - loguru outputs to stdout
        captured = capsys.readouterr()
        assert "processing time is longer than the sampling time" in captured.out
        assert "sampling time must be increased" in captured.out.lower()

    @pytest.mark.asyncio
    async def test_hold_sampling_time_shutdown_event_set(self, shutdown_event):
        """
        Test that the method returns immediately when shutdown event is set.
        
        Verifies that the method checks the shutdown_event and returns
        immediately if it is set, without waiting.
        """
        service = ControllerBasicService(shutdown_event=shutdown_event)
        
        start_time = datetime.now()
        hold_time = 10.0  # Long wait time
        
        await service._hold_sampling_time(start_time, hold_time)
        
        # Should return almost immediately
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed < 0.1  # Less than 100ms

    @pytest.mark.asyncio
    async def test_hold_sampling_time_shutdown_during_wait(self, unset_shutdown_event):
        """
        Test that the method returns when shutdown event is set during wait.
        
        Verifies that the method periodically checks the shutdown_event
        and returns immediately if it becomes set during the wait.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = 10.0  # Long wait time
        
        # Set shutdown event after a short delay
        async def set_shutdown_after_delay():
            await asyncio.sleep(0.05)  # 50ms
            unset_shutdown_event.set()
        
        # Run both tasks concurrently
        await asyncio.gather(
            service._hold_sampling_time(start_time, hold_time),
            set_shutdown_after_delay()
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        # Should return soon after shutdown was set (around 50ms)
        assert elapsed < 0.2  # Less than 200ms

    @pytest.mark.asyncio
    async def test_hold_sampling_time_zero_hold_time(self, unset_shutdown_event):
        """
        Test behavior with zero hold time.
        
        Verifies that the method returns immediately when hold_time is 0.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = 0.0
        
        await service._hold_sampling_time(start_time, hold_time)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed < 0.1  # Should return almost immediately

    @pytest.mark.asyncio
    async def test_hold_sampling_time_negative_hold_time(self, unset_shutdown_event):
        """
        Test behavior with negative hold time.
        
        Verifies that the method returns immediately when hold_time is negative.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = -1.0  # Negative time
        
        await service._hold_sampling_time(start_time, hold_time)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        assert elapsed < 0.1  # Should return almost immediately

    @pytest.mark.asyncio
    async def test_hold_sampling_time_very_short_wait(self, unset_shutdown_event):
        """
        Test behavior with very short hold time.
        
        Verifies that the method handles very short wait times correctly.
        """
        service = ControllerBasicService(shutdown_event=unset_shutdown_event)
        
        start_time = datetime.now()
        hold_time = 0.001  # 1ms
        
        await service._hold_sampling_time(start_time, hold_time)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        # Should wait at least the hold_time (1ms), but likely a bit longer
        assert elapsed >= 0.0005  # At least 0.5ms


class TestServiceLoops:
    """Test class for the main service loop methods."""

    @pytest.mark.asyncio
    async def test_start_service(self, basic_service):
        """
        Test the start_service method.
        
        Verifies that start_service correctly executes the main service loop,
        calling get_data, calculation, prepare_output, and send_outputs in sequence.
        The test uses a shutdown event to ensure the loop runs only once.
        """
        from encodapy.utils.models import InputDataModel
        
        basic_service.config.controller_settings.time_settings.calculation.sampling_time = 0.001
        basic_service.config.controller_settings.time_settings.calculation.sampling_time_unit = TimeUnits.SECOND
        basic_service.config.interfaces.fiware = False
        
        call_counts = {'get_data': 0, 'calculation': 0, 'prepare_output': 0, 'send_outputs': 0}
        
        async def mock_hold_sampling_time(*args, **kwargs):
            # Set shutdown after first iteration to exit loop
            basic_service.shutdown_event.set()
        
        def count_get_data(*args, **kwargs):
            call_counts['get_data'] += 1
            return InputDataModel(input_entities=[], output_entities=[], static_entities=[])
        
        def count_calculation(*args, **kwargs):
            call_counts['calculation'] += 1
            return None
        
        def count_prepare_output(*args, **kwargs):
            call_counts['prepare_output'] += 1
            from encodapy.utils.models import OutputDataModel
            return OutputDataModel(entities=[])
        
        async def count_send_outputs(*args, **kwargs):
            call_counts['send_outputs'] += 1
        
        with patch.object(basic_service, 'get_data', side_effect=count_get_data), \
             patch.object(basic_service, 'calculation', side_effect=count_calculation), \
             patch.object(basic_service, 'prepare_output', side_effect=count_prepare_output), \
             patch.object(basic_service, 'send_outputs', side_effect=count_send_outputs), \
             patch.object(basic_service, 'update_authentication'), \
             patch.object(basic_service, '_hold_sampling_time', side_effect=mock_hold_sampling_time):
            
            # Clear shutdown event so loop runs at least once
            basic_service.shutdown_event.clear()
            await basic_service.start_service()
        
        # Verify all methods were called at least once
        assert call_counts['get_data'] >= 1
        assert call_counts['calculation'] >= 1
        assert call_counts['prepare_output'] >= 1
        assert call_counts['send_outputs'] >= 1

    @pytest.mark.asyncio
    async def test_start_calibration(self, basic_service):
        """
        Test the start_calibration method.
        
        Verifies that start_calibration correctly executes the calibration loop,
        calling get_data and calibration in sequence. The test uses a shutdown
        event to ensure the loop runs only once.
        """
        from encodapy.utils.models import InputDataModel
        from encodapy.config import TimeSettingsCalibrationModel
        
        # Ensure calibration settings exist
        basic_service.config.controller_settings.time_settings.calibration = TimeSettingsCalibrationModel(
            timerange=5.0,
            timerange_unit=TimeUnits.MINUTE,
            sampling_time=0.001,
            sampling_time_unit=TimeUnits.SECOND
        )
        
        call_counts = {'get_data': 0, 'calibration': 0}
        
        async def mock_hold_sampling_time(*args, **kwargs):
            # Set shutdown after first iteration (skip the initial start_hold_time call)
            if call_counts['get_data'] >= 1:
                basic_service.shutdown_event.set()
        
        def count_get_data(*args, **kwargs):
            call_counts['get_data'] += 1
            return InputDataModel(input_entities=[], output_entities=[], static_entities=[])
        
        async def count_calibration(*args, **kwargs):
            call_counts['calibration'] += 1
        
        with patch.object(basic_service, 'get_data', side_effect=count_get_data), \
             patch.object(basic_service, 'calibration', side_effect=count_calibration), \
             patch.object(basic_service, '_hold_sampling_time', side_effect=mock_hold_sampling_time):
            
            # Clear shutdown event so loop runs
            basic_service.shutdown_event.clear()
            await basic_service.start_calibration()
        
        # Verify methods were called
        assert call_counts['get_data'] >= 1
        assert call_counts['calibration'] >= 1

    @pytest.mark.asyncio
    async def test_check_health_status(self, basic_service, unset_shutdown_event):
        """
        Test the check_health_status method.
        
        Verifies that check_health_status correctly calls update_health_file
        and _hold_sampling_time to maintain the service health status.
        The test uses a shutdown event to ensure the loop runs only once.
        """
        call_counts = {'update_health': 0, 'hold_sampling': 0}
        
        async def mock_hold_sampling_time(*args, **kwargs):
            call_counts['hold_sampling'] += 1
            # Set shutdown after first iteration to prevent infinite loop
            unset_shutdown_event.set()
        
        async def mock_update_health(*args, **kwargs):
            call_counts['update_health'] += 1
        
        # Replace shutdown_event with unset_shutdown_event for this test
        basic_service.shutdown_event = unset_shutdown_event
        basic_service.config.controller_settings.time_settings.calculation.sampling_time = 0.001
        basic_service.config.controller_settings.time_settings.calculation.sampling_time_unit = TimeUnits.SECOND
        
        # Patch the module where it's used, not where it's imported from
        with patch('encodapy.service.basic_service.update_health_file', side_effect=mock_update_health), \
             patch.object(basic_service, '_hold_sampling_time', side_effect=mock_hold_sampling_time):
            
            # Clear shutdown event so loop runs
            unset_shutdown_event.clear()
            
            await basic_service.check_health_status()
        
        # Verify methods were called at least once
        assert call_counts['update_health'] >= 1, f"update_health called {call_counts['update_health']} times"
        assert call_counts['hold_sampling'] >= 1, f"hold_sampling called {call_counts['hold_sampling']} times"


class TestHealthTimestamp:
    """Test class for health timestamp functionality."""

    @pytest.mark.asyncio
    async def test_set_health_timestamp(self, basic_service):
        """
        Test the _set_health_timestamp method.
        
        Verifies that _set_health_timestamp correctly sets the timestamp_health
        attribute to the current datetime.
        """
        await basic_service._set_health_timestamp()
        assert basic_service.timestamp_health is not None

    @pytest.mark.asyncio
    async def test_set_health_timestamp_multiple_calls(self, basic_service):
        """
        Test _set_health_timestamp can be called multiple times.
        
        Verifies that the health timestamp is updated on each call.
        """
        first_timestamp = basic_service.timestamp_health
        
        await basic_service._set_health_timestamp()
        second_timestamp = basic_service.timestamp_health
        
        await asyncio.sleep(0.01)
        
        await basic_service._set_health_timestamp()
        third_timestamp = basic_service.timestamp_health
        
        assert second_timestamp != first_timestamp
        assert third_timestamp != second_timestamp

    @pytest.mark.asyncio
    async def test_set_health_timestamp_returns_none(self, basic_service):
        """
        Test that _set_health_timestamp returns None.
        
        Verifies that the method returns None as documented.
        """
        result = await basic_service._set_health_timestamp()
        assert result is None
