"""
Description: This file contains the units for the use and conversion
of different units and in the system controller.
Author: Martin Altenburger
"""

import datetime
from enum import Enum
from typing import Union

from loguru import logger


class TimeUnits(Enum):
    """Possible time units for the time series data

    TODO: Is it better to use standard time units? Like in the unit code?

    """

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
        Union[int, None]: Number of seconds for the time unit\
            or None if the time unit is not available
    """
    if isinstance(time_unit, TimeUnits):
        return TimeUnitsSeconds[time_unit.name].value

    if time_unit in [unit.value for unit in TimeUnits]:
        return TimeUnitsSeconds[TimeUnits(time_unit).name].value

    logger.warning(f"Time unit {time_unit} not available")
    return None


class DataUnits(Enum):
    """
    Possible units for the data
    Units which are defined by Unit Code (https://unece.org/trade/cefact/UNLOCODE-Download 
    or https://github.com/RWTH-EBC/FiLiP/blob/master/filip/data/unece-units/units_of_measure.csv)
    or here: https://unece.org/fileadmin/DAM/cefact/recommendations/rec20/rec20_rev3_Annex3e.pdf
    TODO:
        - Is there a better way to handle the units?
        - Add more units?

    """

    # Time
    SECOND = "SEC"  # "seconds"
    HOUR = "HUR"  # "hour"

    # Temperature
    DEGREECELSIUS = "CEL"  # "°C"

    # Volume / Volumeflow
    LITER = "LTR"  # "l"
    MTQ = "MTW"  # "m³"
    MQH = "MQH"  # "m³/h"

    # Energy / Power
    WTT = "WTT"  # "W"
    WHR = "WHR"  # "Wh"
    KWH = "KWH"  # "kWh"

    # Distance/ Area
    CMT = "CMT"  # "cm"
    MTR = "MTR"  # "m"
    MTK = "MTK"  # "m²"

    MTS = "MTS"  # "m/s"
    P1 = "P1"  # "%"

    # Electrical
    OHM = "OHM"  # "Ohm"
    VLT = "VLT"  # "V"


def get_unit_adjustment_factor(unit_actual: DataUnits, unit_target: DataUnits) -> float:
    """Function to get the adjustment factor for the conversion of units

    Args:
        unit_actual (DataUnits): Actual unit
        unit_target (DataUnits): Target unit

    Returns:
        float: Adjustment factor for the conversion of the units
    """
    # TODO: Real adjustment factors
    raise NotImplementedError(
        "Adjustment factors for the conversion of units are not implemented yet"
    )
