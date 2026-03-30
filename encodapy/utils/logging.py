"""
Description: LoggerControl class to control the log level of the application.
Authors: Martin Altenburger
"""

import sys
from typing import Optional
from pathlib import Path
from datetime import time, timedelta
from loguru import logger


class LoggerControl:
    """
    LoggerControl class for the control of the log level of the application.
    Args:
        log_level (str): The log level for the application, \
            e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
        log_path (Optional[str]): The path to the log file. \
            If not provided, logs will be printed to the console.
        log_rotation (Optional[int | str | time | timedelta]): \
            The rotation policy for the log file. Can be an integer (size in bytes), \
                a string (e.g., '00:00' for daily rotation at midnight), a time object, \
                    or a timedelta object.
        log_retention (Optional[int | str | timedelta]): \
            The retention policy for log files. Can be an integer (number of files to keep), \
                a string (e.g., '7 days'), or a timedelta object.
    """

    def __init__(self,
                 log_level:str,
                 log_path:Optional[str] = None,
                 log_rotation:Optional[int | str | time | timedelta] = None,
                 log_retention:Optional[int | str | timedelta] = None
                 ) -> None:

        logger.remove()
        if isinstance(log_path, str):
            self.prepare_file_logger(log_path, log_level, log_rotation, log_retention)
        else:
            self.add_console_logger(log_level)

    def prepare_file_logger(self,
                            path:str,
                            log_level:str,
                            rotation:Optional[int | str | time | timedelta],
                            retention:Optional[int | str | timedelta]) -> None:
        """
        Prepare the file logger for the application.

        Args:
            path (str): The path to the log file.
            log_level (str): The log level for the file logger.
            rotation (Optional[int | str | time | timedelta]): \
                The rotation policy for the log file.
            retention (Optional[int | str | timedelta]): The number of log files to retain.
        """
        Path(path).parent.mkdir(exist_ok=True)
        logger.add(
            path,
            level=log_level,
            rotation=rotation,
            retention=retention
        )

    def add_console_logger(self, log_level:str) -> None:
        """
        Add a console logger to the application.

        Args:
            log_level (str): The log level for the console logger.
        """
        logger.add(sys.stdout, level=log_level)
