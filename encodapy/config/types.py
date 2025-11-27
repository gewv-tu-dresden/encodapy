"""
Description: Enum classes for the types in the configuration
Authors: Martin Altenburger
"""

from enum import Enum


class Interfaces(Enum):
    """
    Enum class for the interfaces

    Attributes:
        MQTT (str): MQTT interface "mqtt"
        FIWARE (str): FIWARE interface "fiware"
        FILE (str): File interface "file"
    """

    MQTT = "mqtt"
    FIWARE = "fiware"
    FILE = "file"


class AttributeTypes(Enum):
    """
    Enum class for the attribute types
    
    Attributes:
        TIMESERIES (str): Timeseries data "timeseries"
        VALUE (str): Single value data "value"
    """

    TIMESERIES = "timeseries"
    VALUE = "value"


class TimerangeTypes(Enum):
    """
    Enum class for the timedelta types, used for the functions to get timeseries data

    Attributes:
        ABSOLUTE (str): The timedelta is calculated from the actual time "absolute"
        RELATIVE (str): The timedelta is calculated from the last timestamp "relative"
    """

    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class DataQueryTypes(Enum):
    """
    Enum class for the data query types, used for the functions to get data

    Attributes:
        CALCULATION (str): Calculation of the data "calculation"
        CALIBRATION (str): Calibration of the data "calibration"
    """

    CALCULATION = "calculation"
    CALIBRATION = "calibration"


class FileExtensionTypes(Enum):
    """
    Enum class for file Extensions,\
        used for the file interface and defines the possible file formats

    Attributes:
        CSV (str): Comma-separated values "csv"
        JSON (str): JavaScript Object Notation "json"
    """

    CSV = ".csv"
    JSON = ".json"

class MQTTFormatTypes(Enum):
    """
    Enum class for MQTT format types
    Possible values:
    - PLAIN (plain): Plain format
    - FIWARE_ATTR (fiware-attr): FIWARE attribute format
    - FIWARE_CMDEXE (fiware-cmdexe): FIWARE command execution format
    - TEMPLATE (template): Template-based format
    """

    PLAIN = "plain"
    FIWARE_ATTR = "fiware-attr"
    FIWARE_CMDEXE = "fiware-cmdexe"
    TEMPLATE = "template"
