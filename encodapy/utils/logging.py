"""
Description: LoggerControl class to control the log level of the application.
Authors: Martin Altenburger
"""

import sys
from loguru import logger


class LoggerControl:
    """
    LoggerControl class for the control of the log level of the application.
    """

    def __init__(self,
                 log_level:str) -> None:

        logger.remove()
        logger.add(sys.stdout, level=log_level)
