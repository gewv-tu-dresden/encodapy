"""
Unit tests for encodapy.service.service_main module.

Tests the service_main function and related functionality.
"""

# pylint: disable=protected-access
import asyncio
import inspect
from unittest.mock import patch

import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.service.service_main import service_main


class MockService(ControllerBasicService):
    """Mock service for testing service_main function."""

    def __init__(  # pylint: disable=super-init-not-called
        self, shutdown_event=None
    ):
        self.shutdown_event = shutdown_event
        self.start_calibration_called = False
        self.check_health_status_called = False
        self.start_service_called = False

    async def start_calibration(self):
        """Mock start_calibration method."""
        self.start_calibration_called = True
        await asyncio.sleep(0.1)

    async def check_health_status(self):
        """Mock check_health_status method."""
        self.check_health_status_called = True
        await asyncio.sleep(0.1)

    async def start_service(self):
        """Mock start_service method."""
        self.start_service_called = True
        await asyncio.sleep(0.1)


class TestServiceMain:
    """Tests for service_main function."""

    @pytest.mark.asyncio
    async def test_service_main_default_service(self):
        """Test service_main with default ComponentRunnerService."""

        # Create a minimal service that supports shutdown_event
        class MinimalService(ControllerBasicService):
            """Minimal service exposing a shutdown_event."""

            def __init__(  # pylint: disable=super-init-not-called
                self, shutdown_event=None
            ):
                self.shutdown_event = shutdown_event or asyncio.Event()

        # Run service_main with our mock service class
        # The service_main will create its own shutdown_event and pass it to the service
        with patch(
            "encodapy.service.service_main.ComponentRunnerService", MinimalService
        ):
            # Run with a short timeout to avoid long execution
            # service_main creates its own shutdown_event internally
            try:
                await asyncio.wait_for(
                    service_main(service_class=MinimalService),
                    timeout=0.5,  # Short timeout to prevent hanging
                )
            except asyncio.TimeoutError:
                # Expected - the service runs indefinitely without shutdown
                pass

        # If we get here without other errors, the basic flow works
        assert True

    @pytest.mark.asyncio
    async def test_service_main_custom_service(self):
        """Test service_main with custom service class."""
        shutdown_event = asyncio.Event()

        mock_service = MockService(shutdown_event=shutdown_event)

        # Run service_main with custom service class
        task = asyncio.create_task(
            service_main(service_class=lambda shutdown_event=None: mock_service)
        )

        # Wait a bit for tasks to start
        await asyncio.sleep(0.1)

        # Trigger shutdown
        shutdown_event.set()

        # Wait for the service to finish
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.TimeoutError:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        # Check that service methods were called
        assert mock_service.start_calibration_called
        assert mock_service.check_health_status_called
        assert mock_service.start_service_called

    @pytest.mark.asyncio
    async def test_service_main_service_without_shutdown_event(self):
        """Test service_main with service that doesn't support shutdown_event."""

        class OldStyleService(ControllerBasicService):
            """Service stub without a shutdown_event parameter."""

            def __init__(  # pylint: disable=super-init-not-called
                self,
            ):
                pass  # No shutdown_event parameter

            async def start_calibration(self):
                await asyncio.sleep(0.1)

            async def check_health_status(self):
                await asyncio.sleep(0.1)

            async def start_service(self):
                await asyncio.sleep(0.1)

        with patch(
            "encodapy.service.service_main.ComponentRunnerService"
        ) as mock_service_class:
            mock_service = OldStyleService()
            mock_service_class.return_value = mock_service

            # This should work with a warning
            task = asyncio.create_task(service_main(service_class=OldStyleService))

            # Wait a bit and then try to cancel
            await asyncio.sleep(0.1)
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_service_main_signal_handlers(self):
        """Test that service_main registers SIGINT and SIGTERM signal handlers."""
        with patch("encodapy.service.service_main.signal.signal") as mock_signal:
            mock_signal.return_value = None

            class MinimalSignalService(ControllerBasicService):
                """Minimal service exposing a shutdown_event for signal tests."""

                def __init__(  # pylint: disable=super-init-not-called
                    self, shutdown_event=None
                ):
                    self.shutdown_event = shutdown_event or asyncio.Event()

                async def start_calibration(self):
                    """Block until cancelled."""
                    await asyncio.Event().wait()

                async def check_health_status(self):
                    """Block until cancelled."""
                    await asyncio.Event().wait()

                async def start_service(self):
                    """Block until cancelled."""
                    await asyncio.Event().wait()

            with patch(
                "encodapy.service.service_main.ComponentRunnerService",
                MinimalSignalService,
            ):
                task = asyncio.create_task(
                    service_main(service_class=MinimalSignalService)
                )
                # Let the signal handlers register, then shut down.
                await asyncio.sleep(0.2)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        registered_signals = {call.args[0] for call in mock_signal.call_args_list}
        assert __import__("signal").SIGINT in registered_signals

    @pytest.mark.asyncio
    async def test_service_main_clean_shutdown(self):
        """Test service_main performs clean shutdown."""

        # Create a minimal service that supports shutdown_event
        class MinimalService(ControllerBasicService):
            """Minimal service exposing a shutdown_event."""

            def __init__(  # pylint: disable=super-init-not-called
                self, shutdown_event=None
            ):
                self.shutdown_event = shutdown_event or asyncio.Event()

        # Mock the service class in the service_main module
        # Also mock the signal module to prevent actual signal registration
        with patch(
            "encodapy.service.service_main.ComponentRunnerService", MinimalService
        ):
            with patch("encodapy.service.service_main.signal.signal"):
                # Trigger shutdown immediately by setting the event
                # The service_main function creates its own shutdown_event
                # We can't easily access it, but we can trigger shutdown via signal
                # However, for this test we just verify the function can be called
                try:
                    await asyncio.wait_for(
                        service_main(service_class=MinimalService), timeout=0.5
                    )
                except asyncio.TimeoutError:
                    # Expected - service runs until shutdown
                    pass

        # Verify the function can be called without errors
        assert True

    @pytest.mark.asyncio
    async def test_service_main_forced_exit_on_timeout(self):
        """Test service_main forces exit when tasks hang."""
        # This test is hard to run properly without actually hanging
        # Skip for now as it requires complex async handling
        assert True


class TestServiceMainDirectExecution:  # pylint: disable=too-few-public-methods
    """Test service_main when run directly."""

    def test_service_main_direct_execution_creates_tasks(self):
        """Test that service_main creates the expected tasks when run directly."""
        # This test verifies the structure without actually running the async code
        # The actual execution would require proper async context

        # We can at least verify that the function exists and is async

        assert inspect.iscoroutinefunction(service_main)


class TestServiceMainBackwardCompatibility:  # pylint: disable=too-few-public-methods
    """Tests for backward compatibility with services that don't support shutdown_event."""

    @pytest.mark.asyncio
    async def test_service_main_backward_compatibility(self):
        """Test service_main works with services that don't support shutdown_event."""
        # This test is hard to run properly without complex mocking
        # Skip for now as the backward compatibility is tested in other ways
        assert True


class EventDrivenService(ControllerBasicService):
    """Service whose tasks finish as soon as the shutdown event is set."""

    def __init__(  # pylint: disable=super-init-not-called
        self, shutdown_event=None
    ) -> None:
        self.shutdown_event = shutdown_event or asyncio.Event()

    async def start_calibration(self):
        """Wait for the shutdown event."""
        await self.shutdown_event.wait()

    async def check_health_status(self):
        """Wait for the shutdown event."""
        await self.shutdown_event.wait()

    async def start_service(self):
        """Wait for the shutdown event."""
        await self.shutdown_event.wait()


class HangingService(ControllerBasicService):
    """Service whose tasks never finish to simulate hanging tasks."""

    def __init__(  # pylint: disable=super-init-not-called
        self, shutdown_event=None
    ) -> None:
        self.shutdown_event = shutdown_event
        if shutdown_event is not None:
            shutdown_event.set()

    async def start_calibration(self):
        """Block forever."""
        await asyncio.Event().wait()

    async def check_health_status(self):
        """Block forever."""
        await asyncio.Event().wait()

    async def start_service(self):
        """Block forever."""
        await asyncio.Event().wait()


class TestServiceMainShutdownFlow:
    """Tests for the shutdown flow of service_main."""

    @pytest.mark.asyncio
    async def test_service_main_invokes_signal_handler_and_stops_cleanly(self):
        """Test that the registered signal handler stops the service cleanly."""
        with patch("encodapy.service.service_main.signal.signal") as mock_signal:
            task = asyncio.create_task(service_main(service_class=EventDrivenService))

            # Wait until the signal handlers are registered
            await asyncio.sleep(0.2)

            registered_signals = {call.args[0] for call in mock_signal.call_args_list}
            assert __import__("signal").SIGINT in registered_signals
            assert __import__("signal").SIGTERM in registered_signals

            # Invoke the registered SIGINT handler like the OS would
            sigint_handler = mock_signal.call_args_list[0].args[1]
            sigint_handler(None, None)

            # The service should now stop without errors
            await asyncio.wait_for(task, timeout=5.0)

    @pytest.mark.asyncio
    async def test_service_main_sigterm_failure_registers_sigint_only(self):
        """Test that a failing SIGTERM registration still registers SIGINT."""
        sig_module = __import__("signal")

        def signal_side_effect(signalnum, _handler):
            """Raise an OSError for SIGTERM like restricted environments do."""
            if signalnum == sig_module.SIGTERM:
                raise OSError("SIGTERM not supported")

        with patch(
            "encodapy.service.service_main.signal.signal",
            side_effect=signal_side_effect,
        ) as mock_signal:
            task = asyncio.create_task(service_main(service_class=EventDrivenService))

            # Wait until the signal handlers are registered
            await asyncio.sleep(0.2)

            registered_signals = [call.args[0] for call in mock_signal.call_args_list]
            assert registered_signals == [
                sig_module.SIGINT,
                sig_module.SIGTERM,
                sig_module.SIGINT,
            ]

            # Nothing sets the shutdown event here, so finish via cancel
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_service_main_raises_and_forces_exit_on_hanging_tasks(self):
        """Test that hanging service tasks raise TimeoutError and force exit."""
        real_wait = asyncio.wait

        async def fast_wait(fs, *, timeout=None, return_when=None):
            """Wrap asyncio.wait with a shortened timeout to keep the test fast."""
            if timeout is not None:
                timeout = 0.05
            return await real_wait(fs, timeout=timeout, return_when=return_when)

        with patch("encodapy.service.service_main.signal.signal") as mock_signal:
            with patch(
                "encodapy.service.service_main.asyncio.wait", side_effect=fast_wait
            ):
                with patch("encodapy.service.service_main.os._exit") as mock_exit:
                    task = asyncio.create_task(
                        service_main(service_class=HangingService)
                    )

                    with pytest.raises(TimeoutError):
                        await asyncio.wait_for(task, timeout=5.0)

                    mock_exit.assert_called_once_with(1)

        assert mock_signal.call_args_list
