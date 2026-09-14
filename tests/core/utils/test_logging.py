"""Tests for the application logging configuration."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from encodapy.utils.logging import LoggerControl


class TestLoggerControl:
    """Test logger configuration and normalization."""

    @patch("encodapy.utils.logging.logger.remove")
    @patch("encodapy.utils.logging.logger.add")
    def test_normalizes_numeric_environment_values(
        self, mock_add, mock_remove, tmp_path: Path
    ):
        """Numeric strings are passed to Loguru as integers."""
        log_path = tmp_path / "logs" / "service.log"

        LoggerControl(
            "INFO",
            str(log_path),
            log_rotation="10485760",
            log_retention="5",
        )

        mock_add.assert_called_once_with(
            str(log_path),
            level="INFO",
            rotation=10485760,
            retention=5,
        )

    @patch("encodapy.utils.logging.logger.remove")
    @patch("encodapy.utils.logging.logger.add")
    def test_preserves_loguru_text_and_timedelta_values(
        self, mock_add, mock_remove, tmp_path: Path
    ):
        """Non-numeric Loguru values are passed through unchanged."""
        log_path = tmp_path / "service.log"
        retention = timedelta(days=7)

        LoggerControl(
            "INFO",
            str(log_path),
            log_rotation="1 day",
            log_retention=retention,
        )

        mock_add.assert_called_once_with(
            str(log_path),
            level="INFO",
            rotation="1 day",
            retention=retention,
        )

    @patch("encodapy.utils.logging.logger.remove")
    @patch("encodapy.utils.logging.logger.add")
    def test_creates_nested_log_directories(
        self, mock_add, mock_remove, tmp_path: Path
    ):
        """All missing parent directories for a log file are created."""
        log_path = tmp_path / "logs" / "service" / "service.log"

        LoggerControl("INFO", str(log_path))

        assert log_path.parent.is_dir()
        mock_add.assert_called_once()
