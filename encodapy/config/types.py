"""
Description: Enum classes for the types in the configuration
Authors: Martin Altenburger
"""

from enum import Enum


class Interfaces(Enum):
    """
    Enum class for the interfaces
    Possible values:
    - MQTT (mqtt): MQTT interface
    - FIWARE (fiware): FIWARE interface
    - FILE (file): File interface
    """

    MQTT = "mqtt"
    FIWARE = "fiware"
    FILE = "file"


class AttributeTypes(Enum):
    """
    Enum class for the attribute types
    Possible values:
    - TIMESERIES (timeseries): Timeseries data
    - VALUE (value): Single value data
    """

    TIMESERIES = "timeseries"
    VALUE = "value"


class TimerangeTypes(Enum):
    """Enum class for the timedelta types

    Possible values:
    - ABSOLUTE (absolute): The timedelta is calculated from the actual time
    - RELATIVE (relative): The timedelta is calculated from the last timestamp
    """

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class DataQueryTypes(Enum):
    """
    Enum class for the data query types
    Possible values:
    - CALCULATION (calculation): Calculation of the data
    - CALIBRATION (calibration): Calibration of the data
    """

    CALCULATION = "calculation"
    CALIBRATION = "calibration"


class FileExtensionTypes(Enum):
    """
    Enum class for file Extensions
    Possible values:
    - CSV (csv): Comma-separated values
    - JSON (json): JavaScript Object Notation
    """

    CSV = ".csv"
    JSON = ".json"

class MQTTFormatTypes(Enum):
    """
    Enum class for MQTT format types
    Possible values:
    - PLAIN (plain): Plain format
    - JSON (json): JSON format
    """

    PLAIN = "plain"
    FIWARE_ATTR = "fiware-attr"
    FIWARE_CMDEXE = "fiware-cmdexe"
    TEMPLATE = "template"
