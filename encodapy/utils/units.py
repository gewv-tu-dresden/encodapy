"""
Description: This file contains the units for the use and conversion
of different units and in the system controller.
Author: Martin Altenburger
"""

from enum import Enum
from typing import Union, Optional
import pint
import pandas as pd
from loguru import logger
from encodapy.utils.deprecated import deprecated


class TimeUnits(Enum):
    """Possible time units for the time series data

    TODO: Is it better to use standard time units? Like in the unit code?

    """

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


class DataUnits(Enum):
    """
    Possible units for the data
    Units which are defined by Unit Code (https://unece.org/trade/cefact/UNLOCODE-Download
    or https://github.com/RWTH-EBC/FiLiP/blob/master/filip/data/unece-units/units_of_measure.csv)
    or here: https://unece.org/fileadmin/DAM/cefact/recommendations/rec20/rec20_rev3_Annex3e.pdf
    
    The enum value is the standardized unit code (e.g., "SEC" for seconds).
    The pint_unit attribute contains the corresponding pint unit string for conversion.
    
    To add a new unit, add it to the DataUnits enum: UNIT_NAME = ("CODE", "pint_string")
    The _UNIT_MAP will be generated automatically from the pint_unit attributes.
    
    Usage:
        - DataUnits.PERCENT.value -> "P1" (unit code, for serialization)
        - DataUnits.PERCENT.pint_unit -> "percent" (for pint conversion)
        - DataUnits("P1") -> DataUnits.PERCENT (lookup by unit code)
    """

    pint_unit: str  # Type annotation for the attribute set in __new__

    def __new__(cls, unit_code: str, pint_unit: str = ""):
        # pint_unit has a default for type checking during lookup (DataUnits("CEL"))
        # but is always required when defining enum members
        obj = object.__new__(cls)
        obj._value_ = unit_code  # This makes .value return the unit_code
        obj.pint_unit = pint_unit if pint_unit else unit_code
        return obj

    # Time
    SECOND = ("SEC", "second")
    HOUR = ("HUR", "hour")
    MINUTE = ("MIN", "minute")
    DAY = ("DAY", "day")
    MONTH = ("MON", "month")
    YEAR = ("ANN", "year")

    # Temperature
    DEGREECELSIUS = ("CEL", "degC")
    KELVIN = ("KEL", "kelvin")

    # Volume / Volumeflow
    LITER = ("LTR", "liter")
    MTQ = ("MTQ", "meter**3")
    MQH = ("MQH", "meter**3 / hour")
    MQS = ("MQS", "meter**3 / second")
    E32 = ("E32", "liter / hour")
    L2 = ("L2", "liter / minute")

    # Energy / Power
    WTT = ("WTT", "watt")
    KWT = ("KWT", "kilowatt")
    WHR = ("WHR", "watt_hour")
    KWH = ("KWH", "kilowatt_hour")

    # Distance/ Area
    CMT = ("CMT", "centimeter")
    MTR = ("MTR", "meter")
    MTK = ("MTK", "meter**2")

    # speed
    MTS = ("MTS", "meter / second")

    # unitless
    PERCENT = ("P1", "percent")

    # Electrical
    OHM = ("OHM", "ohm")
    VLT = ("VLT", "volt")

# Map the units to the unit registry of pint for conversion
# This is automatically generated from the DataUnits enum
_ureg: pint.UnitRegistry = pint.UnitRegistry()
_UNIT_MAP: dict[DataUnits, str] = {unit: unit.pint_unit for unit in DataUnits}


@deprecated("Use adjust_unit_of_value instead. Will be removed in future versions.")
def get_unit_adjustment_factor(
    unit_actual: DataUnits, unit_target: DataUnits
) -> Optional[float]:
    """Function to get the adjustment factor for the conversion of units

    It is recommended to use adjust_units instead, which directly adjusts the value \
    and unit of a datapoint, \
    and handles more complex cases (e.g., DataFrames, Series, lists, dicts) \
    and also handles the case when the value is None or not a number.

    This function is still available for backward compatibility, \
        but will be removed in future versions. 
    It is recommended to switch to adjust_units, which is more robust and handles more cases.

    Args:
        unit_actual (DataUnits): Actual unit
        unit_target (DataUnits): Target unit

    Returns:
        Optional[float]: Adjustment factor for the conversion of the units, if found

    TODO: Remove the function
    """

    try:
        assert unit_actual is not None, "Actual unit is None, cannot determine adjustment factor"
        assert unit_target is not None, "Target unit is None, cannot determine adjustment factor"
    except AssertionError as exc:
        logger.warning("Cannot determine adjustment factor: " + str(exc))
        return None

    if unit_actual == unit_target:
        return 1.0
    if unit_actual in [DataUnits.KELVIN, DataUnits.DEGREECELSIUS]:
        logger.warning(
            "Cannot determine adjustment factor for temperature "
            f"units {unit_actual} and {unit_target}"
        )
        return None
    try:
        actual = _UNIT_MAP[unit_actual]
        target = _UNIT_MAP[unit_target]
        assert unit_actual not in [DataUnits.KELVIN, DataUnits.DEGREECELSIUS], \
            "Temperature units are not supported for adjustment factor calculation"
    except (KeyError, AssertionError) as exc:
        logger.warning(f"Could not map the unit for {unit_actual} or {unit_target}: {exc}")
        return None

    try:
        q = (1 * _ureg.parse_expression(actual)).to(target)
        return float(q.magnitude)
    except pint.DimensionalityError as exc:
        logger.warning(f"Incompatible units: {unit_actual} -> {unit_target}: {exc}")
        return None

def adjust_unit_of_value(
    value: float | int,
    unit_actual: DataUnits,
    unit_target: DataUnits
    ) -> Optional[float]:
    """Function to adjust the unit of a value.

    Args:
        value (float | int): Value to adjust.
        unit_actual (DataUnits): Actual unit of the value
        unit_target (DataUnits): Target unit of the value

    Returns:
        Optional[float]: Adjusted value, if adjustment factor could be determined.
    """
    if unit_actual == unit_target:
        return value

    if not isinstance(value, (int, float)):
        raise ValueError(f"Value must be a float or int for unit adjustment, got {type(value)}")
    try:
        actual = _UNIT_MAP[unit_actual]
        target = _UNIT_MAP[unit_target]
    except KeyError as exc:
        logger.warning(f"Unit mapping missing for {unit_actual} or {unit_target}")
        raise ValueError(f"Unit mapping missing for {unit_actual} or {unit_target}") from exc

    try:

        q = (value * _ureg.parse_expression(actual)).to(target)
        return float(q.magnitude)

    except pint.DimensionalityError as exc:
        logger.warning(f"Incompatible units: {unit_actual} -> {unit_target}: {exc}")
        raise ValueError(f"Incompatible units: {unit_actual} -> {unit_target}: {exc}") from exc

def adjust_units(
    value: Optional[Union[str, float, int, pd.DataFrame, pd.Series, list, dict, bool]],
    unit_actual: Optional[DataUnits],
    unit_target: Optional[DataUnits],
    column_name: Optional[str] = None
    ) -> Optional[Union[str, float, int, pd.DataFrame, pd.Series, list, dict, bool]]:
    """
    Function to adjust the unit of a datapoint.
    To use this function, simply pass the value, the actual unit and the target unit, like:

    .. code-block:: python

        adjusted_value = adjust_units(
            value=10,
            unit_actual=DataUnits.SECOND,
            unit_target=DataUnits.MINUTE
        )


    Args:
        value (Optional[Union[str, float, int, pd.DataFrame, pd.Series, list, dict, bool]]): \
            Value to adjust
        unit_actual (Optional[DataUnits]): Actual unit of the value
        unit_target (Optional[DataUnits]): Target unit of the value
        column_name (Optional[str]): Name of the column to adjust, if value is a DataFrame

    Returns:
        Optional[Union[str, float, int, pd.DataFrame, pd.Series, list, dict, bool]]: \
            Datapoint with adjusted unit, if adjustment factor could be determined, otherwise None

    """
    try:
        assert unit_actual is not None, "Actual unit is None, cannot adjust unit"
        assert unit_target is not None, "Target unit is None, cannot adjust unit"
        assert value is not None, "Value is None, cannot adjust unit"
    except AssertionError as exc:
        logger.warning("Cannot adjust unit: " + str(exc))
        return None

    if unit_actual == unit_target:
        return value
    adjusted_value: Optional[Union[str, float, int, pd.DataFrame, pd.Series, list, dict, bool]]
    try:
        if isinstance(value, (bool, str)):
            logger.debug(f"Value is {type(value).__name__}, cannot adjust unit")
            adjusted_value = value
        elif isinstance(value, (int, float)):
            adjusted_value = adjust_unit_of_value(
                value=value, unit_actual=unit_actual, unit_target=unit_target
            )
        elif isinstance(value, pd.DataFrame):
            adjusted_value = value.copy()
            column = column_name if column_name is not None else adjusted_value.columns[0]
            adjusted_value[column] = adjusted_value[column].apply(
                lambda x: adjust_unit_of_value(x, unit_actual, unit_target)
            )
        elif isinstance(value, pd.Series):
            adjusted_value = value.copy()
            adjusted_value = adjusted_value.apply(
                lambda x: adjust_unit_of_value(x, unit_actual, unit_target)
            )
        elif isinstance(value, list):
            adjusted_value = [
                adjust_unit_of_value(x, unit_actual, unit_target) for x in value
            ]
        elif isinstance(value, dict):
            try:
                adjusted_value = {
                    k: adjust_unit_of_value(v, unit_actual, unit_target)
                    for k, v in value.items()
                }
            except ValueError as exc:
                logger.warning(f"Value in dict cannot be adjusted: {exc}")
                adjusted_value = value
        else:
            logger.warning(f"Value type {type(value)} not supported for unit adjustment")
            adjusted_value = value

        return adjusted_value
    except ValueError as exc:
        logger.warning(f"Unit adjustment failed with ValueError: {exc}")
        return None

def get_time_unit_seconds(
    time_unit: Union[TimeUnits, str, DataUnits],
) -> Optional[float]:
    """Function to get the seconds for a time unit using pint

    Args:
        time_unit (Union[TimeUnits, str, DataUnits]): time unit / Name of the time unit \
            If you use DataUnits, only the units which are also in TimeUnits are valid

    Returns:
        Optional[float]: Number of seconds for the time unit\
            or None if the time unit is not available
    """
    try:
        # Convert input to TimeUnits if needed
        if isinstance(time_unit, TimeUnits):
            unit_name = time_unit.name.lower()
        elif isinstance(time_unit, DataUnits):
            unit_name = time_unit.name.lower()
        elif isinstance(time_unit, str):
            unit_name = time_unit.lower()
        else:
            logger.warning(f"Time unit type {type(time_unit)} not supported")
            return None

        # Convert to seconds using pint
        unit_expr = _ureg.parse_expression(unit_name)
        seconds = (1 * unit_expr).to("second").magnitude
        return float(seconds)

    except pint.UndefinedUnitError as exc:
        logger.warning(f"Time unit '{time_unit}' is not defined in pint: {exc}")
        return None
    except pint.DimensionalityError as exc:
        logger.warning(f"Time unit '{time_unit}' cannot be converted to seconds: {exc}")
        return None
    except AttributeError as exc:
        logger.warning(f"Invalid time unit input '{time_unit}': {exc}")
        return None
