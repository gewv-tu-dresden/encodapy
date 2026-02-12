"""
Description: This file contains the units for the use and conversion
of different units and in the system controller.
Author: Martin Altenburger
"""

import datetime
from enum import Enum
from typing import Union, Optional

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
    MINUTE = "MIN"  # "minute"

    # Temperature
    DEGREECELSIUS = "CEL"  # "°C"
    KELVIN = "KEL"  # "K"

    # Volume / Volumeflow
    LITER = "LTR"  # "l"
    MTQ = "MTQ"  # "m³"
    MQH = "MQH"  # "m³/h"
    MQS = "MQS"  # "m³/s"
    E32 = "E32"  # "l/h" (E32 is the unit code for liters per hour)
    L2 = "L2"  # "l/m" (L2 is the unit code for liters per minute)

    # Energy / Power
    WTT = "WTT"  # "W"
    KWT = "KWT"  # "kW"
    WHR = "WHR"  # "Wh"
    KWH = "KWH"  # "kWh"

    # Distance/ Area
    CMT = "CMT"  # "cm"
    MTR = "MTR"  # "m"
    MTK = "MTK"  # "m²"

    # speed
    MTS = "MTS"  # "m/s"

    # unitless
    PERCENT = "P1"  # "%"

    # Electrical
    OHM = "OHM"  # "Ohm"
    VLT = "VLT"  # "V"


def get_unit_adjustment_factor(
    unit_actual: DataUnits, unit_target: DataUnits
) -> Optional[float]:
    """Function to get the adjustment factor for the conversion of units

    Args:
        unit_actual (DataUnits): Actual unit
        unit_target (DataUnits): Target unit

    Returns:
        Optional[float]: Adjustment factor for the conversion of the units, if found
    """

    if unit_actual is None:
        logger.warning("Actual unit is None, could not determine adjustment factor")
        return None
    if unit_target is None:
        logger.warning("Target unit is None, could not determine adjustment factor")
        return None
    if unit_actual == unit_target:
        return 1.0
    # TODO: Real adjustment factors
    logger.warning(
        f"Adjustment factor for the conversion of {unit_actual} to {unit_target} "
        "not implemented yet"
    )
    return None


def get_time_unit_seconds(
    time_unit: Union[TimeUnits, str, DataUnits],
) -> Optional[float]:
    """Funktion to get the seconds for a time unit

    Args:
        time_unit (Union[TimeUnits, str, DataUnits]): time unit / Name of the time unit \
            If you use DataUnits, only the units which are also in TimeUnits are valid

    Returns:
        Union[int, None]: Number of seconds for the time unit\
            or None if the time unit is not available
    """
    if isinstance(time_unit, TimeUnits):
        return TimeUnitsSeconds[time_unit.name].value

    if time_unit in [unit.value for unit in TimeUnits]:
        return TimeUnitsSeconds[TimeUnits(time_unit).name].value

    if isinstance(time_unit, DataUnits):
        return TimeUnitsSeconds[TimeUnits[time_unit.name].name].value

    if time_unit in [unit.name for unit in DataUnits]:
        if DataUnits(time_unit).name in [unit.name for unit in TimeUnits]:
            return TimeUnitsSeconds[TimeUnits(DataUnits(time_unit).name).name].value

    logger.warning(f"Time unit {time_unit} not available")
    return None
