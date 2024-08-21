# Description: This file contains the time units for the use and conversion of different time units and  in the system controller.
# Author: Martin Altenburger

import datetime
from enum import Enum
from typing import Union

from loguru import logger


class TimeUnits(Enum):
    """Possible time units for the time series data"""

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class TimeUnitsSeconds(Enum):
    """Seconds for the time units"""

    SECOND = datetime.timedelta(seconds=1).total_seconds()
    MINUTE = datetime.timedelta(minutes=1).total_seconds()
    HOUR = datetime.timedelta(hours=1).total_seconds()
    DAY = datetime.timedelta(days=1).total_seconds()
    MONTH = datetime.timedelta(days=30).total_seconds()


def get_time_unit_seconds(time_unit: Union[TimeUnits, str]) -> Union[int, None]:
    """Funktion to get the seconds for a time unit

    Args:
        time_unit (Union[TimeUnits, str]): time unit / Name of the time unit

    Returns:
        Union[int, None]: Number of seconds for the time unit or None if the time unit is not available
    """
    if isinstance(time_unit, TimeUnits):
        return TimeUnitsSeconds[time_unit.name].value

    elif time_unit in [unit.value for unit in TimeUnits]:
        return TimeUnitsSeconds[TimeUnits(time_unit).name].value
    else:
        logger.warning(f"Time unit {time_unit} not available")
        return None
