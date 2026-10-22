"""
Description: This file contains the models for the configuration of the system controller.
Authors: Martin Altenburger
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import pandas as pd
from filip.models.base import DataType
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.functional_validators import model_validator

from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.config.types import (
    AttributeTypes,
    Interfaces,
    MQTTFormatTypes,
    TimerangeTypes,
)
from encodapy.utils.error_handling import ConfigError, InterfaceNotActive
from encodapy.utils.units import DataUnits, TimeUnits

# Import MQTTTemplateConfigDoc for sphinx documentation generation
IS_BUILDING_DOCS = "BUILDING_DOCS" in os.environ
if TYPE_CHECKING or not IS_BUILDING_DOCS:
    from encodapy.config.mqtt_messages_template import MQTTTemplateConfig
else:
    from encodapy.config.mqtt_messages_template import (
        MQTTTemplateConfigDoc as MQTTTemplateConfig,
    )


class InterfaceModel(BaseModel):
    """
    Base class for the interfaces

    Attributes:
        mqtt (bool): Whether the MQTT interface is active. Defaults to False.
        fiware (bool): Whether the FIWARE interface is active. Defaults to False.
        file (bool): Whether the FILE interface is active. Defaults to False.
    """

    mqtt: bool = False
    fiware: bool = False
    file: bool = False


class AttributeModel(BaseModel):
    """
    Configuration class for representing attributes with metadata, value, \
        and optional interface-specific identifier.

    This class models attributes with a unique ID, type, value, unit, and timestamp.
    If `id_interface` is not set, it defaults to the value of `id`.

    Attributes:
        id (str): The unique identifier of the attribute.
        id_interface (str): The interface-specific identifier. Defaults to `None`.
            If not set, it will be automatically set to the value of `id`.
        type (AttributeTypes): The type of the attribute. Defaults to `AttributeTypes.VALUE`.
        value (Union[str, float, int, bool, Dict, List, pd.DataFrame, pd.Series, None]): \
            The value of the attribute. Defaults to `None`.
        unit (Optional[DataUnits]): The unit of measurement for the value. Defaults to `None`.
        datatype (DataType): The data type of the attribute. Defaults to `DataType("Number")`.
        timestamp (Optional[datetime]): The timestamp of the attribute. Defaults to `None`.
        mqtt_format (Union[MQTTFormatTypes, MQTTTemplateConfig]): \
            The format of the attribute for MQTT (if not set, the default format is used) \
                - only for mqtt interface needed
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = Field(default="")
    type: AttributeTypes = AttributeTypes.VALUE
    value: str | float | int | bool | dict | list | pd.DataFrame | pd.Series | None = (
        None
    )
    unit: DataUnits | None = None
    datatype: DataType = DataType("Number")
    timestamp: datetime | None = None
    mqtt_format: MQTTFormatTypes | MQTTTemplateConfig = MQTTFormatTypes.PLAIN

    @model_validator(mode="after")
    def set_id_interface(self) -> "AttributeModel":
        """
        Sets the 'id_interface' attribute to the value of 'id' if it is currently None.

        Returns:
            AttributeModel: The instance with the updated 'id_interface' attribute.
        """
        if self.id_interface == "":
            self.id_interface = self.id
        return self


class CommandModel(BaseModel):
    """
    Configuration class for the commands

    Attributes:
        id (str): The id of the command
        id_interface (str | None): The id of the command on the interface \
            (if not set, the id is used)
        value (Union[str, int, float, List, Dict, None]): The value of the command
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = Field(default="")
    value: str | int | float | list | dict | bool | None = None

    @model_validator(mode="after")
    def set_id_interface(self) -> "CommandModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface == "":
            self.id_interface = self.id
        return self


class InputModel(BaseModel):
    """
    Model for the configuration of inputs.

    Attributes:
        id (str): The id of the input
        interface (Interfaces): The interface of the input
        id_interface (str | None): The id of the input on the interface, default is the id
        attributes (list[AttributeModel]): A list of attributes for the input as AttributeModel

    """

    id: str
    interface: Interfaces
    id_interface: str = Field(default="")
    attributes: list[AttributeModel]

    @model_validator(mode="after")
    def set_id_interface(self) -> "InputModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface == "":
            self.id_interface = self.id
        return self


class StaticDataModel(InputModel):
    """
    Model for the configuration of inputs.

    Attributes:
        id (str): The id of the input
        interface (Interfaces): The interface of the input
        id_interface (str | None): The id of the input on the interface
        attributes (list[AttributeModel]): A list of attributes for the static data \
            as AttributeModel

    """


class OutputModel(BaseModel):
    """
    Model for the configuration of outputs.

    Attributes:
        id: The id of the output
        interface: The interface of the output
        id_interface: The id of the output on the interface, default is the id
        attributes: The attributes of the output
    """

    id: str
    interface: Interfaces
    id_interface: str = Field(default="")
    attributes: list[AttributeModel]
    commands: list[CommandModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_id_interface(self) -> "OutputModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface == "":
            self.id_interface = self.id
        return self


class TimeSettingsCalculationModel(BaseModel):
    """
    Base class for the calculation time settings of the controller / system.

    Attributes:
        timerange: The timerange for the calculation (if only one value is needed and primary value\
            , otherwise use timerange_min and timerange_max)
        timerange_min: The minimum timerange for the calculation (only used if timerange is not set\
            and timerange_max is set too)
        timerange_max: The maximum timerange for the calculation (only used if timerange is not set\
            and timerange_min is set too)
        timerange_type: Type of time period, relative to the last result or absolute at the current\
            time (if not set, the default type is absolute)
        timerange_unit: The unit of the timerange (if not set, the default unit is minute)
        timestep: The timestep for the calculation (if not set, the default value is 1), the\
            related unit is defined in the timestep_unit attribute
        timestep_unit: The unit of the timestep (if not set, the default unit is second)
        sampling_time: The sampling time for the calculation (if not set, the default value is 1),\
            the related unit is defined in the sampling_time_unit attribute
        sampling_time_unit: The unit of the sampling time (if not set, the default unit is minute)
    """

    timerange: float | None = None
    timerange_min: float | None = None
    timerange_max: float | None = None
    timerange_type: TimerangeTypes | None = TimerangeTypes.ABSOLUTE
    timerange_unit: TimeUnits = TimeUnits.MINUTE

    timestep: float | int = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND

    sampling_time: float | int = 1
    sampling_time_unit: TimeUnits = TimeUnits.MINUTE

    @model_validator(mode="after")
    def check_timerange_parameters(self) -> "TimeSettingsCalculationModel":
        """Check the timerange parameters.

        Raises:
            ValueError: If the timerange parameters are not set correctly

        Returns:
            TimeSettingsCalculationModel: The model with the validated parameters
        """

        if self.timerange is None and (
            self.timerange_min is None or self.timerange_max is None
        ):
            raise ValueError(
                "Either 'timerange' or 'timerange_min' and 'timerange_max' must be set."
            )

        if self.timerange is not None and (
            self.timerange_min is not None or self.timerange_max is not None
        ):
            logger.warning(
                "Either 'timerange' or both 'timerange_min' and 'timerange_max' should be set, \
                not both. Using 'timerange' as the only value."
            )

            self.timerange_min = None
            self.timerange_max = None

        return self

    @model_validator(mode="before")
    @classmethod
    def check_timestep_units(cls, data: Any) -> Any:
        """Checks the units of the times in the configuration and provides feedback (debug logging)
        if the default values are used

        Args:
            data (Any): The data to check (input data)

        Returns:
            Any: The data with the checked timestep units
        """
        if "timestep" not in data:
            logger.debug("No timestep is set - using default value '1'")
        if "timestep_unit" not in data:
            logger.debug("No timestep unit is set - using default unit 'second'")
        if "sampling_time" not in data:
            logger.debug("No sampling time is set - using default value '1'")
        if "sampling_time_unit" not in data:
            logger.debug("No sampling time unit is set - using default unit 'minute'")
        if "timerange_unit" not in data:
            logger.debug("No timerange unit is set - using default unit 'minute'")
        if "timerange_type" not in data:
            logger.debug("No timerange type is set - using default type 'absolute'")
        return data


class TimeSettingsCalibrationModel(BaseModel):
    """
    Base class for the calibration time settings of the controller / system.

    Attributes:
        timerange: The timerange for the calibration (if not set, the default value is 1), \
            the related unit is defined in the timerange_unit attribute
        timerange_unit: The unit of the timerange (if not set, the default unit is minute)
        timestep: The timestep for the calibration (if not set, the default value is 1), \
            the related unit is defined in the timestep_unit attribute
        timestep_unit: The unit of the timestep (if not set, the default unit is second)
        sampling_time: The sampling time for the calibration (if not set, the default value is 1), \
            the related unit is defined in the sampling_time_unit attribute
        sampling_time_unit: The unit of the sampling time (if not set, the default unit is day)

    """

    timerange: float | None = None
    timerange_unit: TimeUnits = TimeUnits.MINUTE

    timestep: float | int = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND

    sampling_time: float | int = 1
    sampling_time_unit: TimeUnits = TimeUnits.DAY


class TimeSettingsModel(BaseModel):
    """
    Base class for the time settings of the controller / system.

    Attributes:
        calculation: The timeranges and settings für the calculation
        calibration: The timeranges and settings for the calibration
    """

    calculation: TimeSettingsCalculationModel
    calibration: TimeSettingsCalibrationModel | None = None


class ConfigModel(BaseModel):
    """
    Base model for the configuration of the system controller.

    Attributes:
        interfaces (InterfaceModel): Configuration of the system controller interfaces.
        inputs (list[InputModel]): List of input configurations for the system controller.
        outputs (ist[OutputModel]): Output configurations for the system controller.
        staticdata (list[StaticDataModel]): \
            Static configuration data for devices managed by the system controller.
        controller_components (list[ControllerComponentModel]): Components used by the controller.
        time_settings (TimeSettingsModel): Time settings for the controller.
    """

    interfaces: InterfaceModel
    inputs: list[InputModel]
    outputs: list[OutputModel]
    staticdata: list[StaticDataModel]

    controller_components: list[ControllerComponentModel]

    time_settings: TimeSettingsModel

    @classmethod
    def from_json(cls, file_path: str):
        """
        Load the configuration from a JSON file.
        """

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return cls(**config_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Couldn't load the json file: {e}")
        except ValidationError as e:
            logger.error(e)

        raise ConfigError("Coudn't load configuration from json file")

    @model_validator(mode="before")
    @classmethod
    def migrate_deprecated_settings(cls, data: Any) -> Any:
        """Migrates deprecated configuration keys to the current structure.

        The deprecated key 'controller_settings' is transformed into
        'time_settings'. The deprecated 'specific_settings' and the time
        settings 'results' are not used anymore and are dropped.

        Args:
            data (Any): The data to migrate

        Returns:
            Any: The migrated data
        """
        if not isinstance(data, dict):
            return data

        if "controller_settings" in data:
            controller_settings = data.pop("controller_settings")
            logger.warning(
                "The key 'controller_settings' is deprecated - "
                "use 'time_settings' instead."
            )
            if isinstance(controller_settings, dict):
                if "specific_settings" in controller_settings:
                    logger.warning(
                        "'specific_settings' is deprecated and not used "
                        "anymore - the settings are dropped."
                    )
                data.setdefault(
                    "time_settings", controller_settings.get("time_settings")
                )

        if (
            isinstance(data.get("time_settings"), dict)
            and "results" in data["time_settings"]
        ):
            logger.warning(
                "'results' in the time settings is deprecated and not used "
                "anymore - the settings are dropped."
            )
            data["time_settings"].pop("results")

        return data

    @model_validator(mode="after")
    def check_interfaces(self) -> "ConfigModel":
        """Check the interfaces of the input / output.

        Raises:
            ValueError: If no interface is set or the interface is not active \
                and in use for input or output

        Returns:
            ConfigModel: The model with the validated interfaces
        """

        if not any(
            [self.interfaces.mqtt, self.interfaces.fiware, self.interfaces.file]
        ):
            raise InterfaceNotActive("At least one interface must be set.")

        def check_interface_active(
            datapoints: list[InputModel] | list[StaticDataModel] | list[OutputModel],
        ) -> None:
            """
            Check if the interface is active for the datapoints.

            Args:
                datapoints (Union[InputModel, StaticDataModel, OutputModel]): \
                    The datapoints to check

            Raises:
                ValueError: If the datapoints are not valid
                InterfaceNotActive: If the interface is not active \
                    but used for the datapoints
            """
            if len(datapoints) == 0:
                return
            if isinstance(datapoints[0], InputModel):
                config_part = "input"
            elif isinstance(datapoints[0], StaticDataModel):
                config_part = "static data"
            elif isinstance(datapoints[0], OutputModel):
                config_part = "output"
            else:
                raise ValueError("The input data is not valid")

            for datapoint in datapoints:
                if datapoint.interface == Interfaces.MQTT and not self.interfaces.mqtt:
                    raise InterfaceNotActive(
                        f"The MQTT interface is used for the {config_part} '{datapoint.id}', "
                        "but not set in the configuration."
                    )
                if (
                    datapoint.interface == Interfaces.FIWARE
                    and not self.interfaces.fiware
                ):
                    raise InterfaceNotActive(
                        f"The FIWARE interface is used for the {config_part} '{datapoint.id}', "
                        "but not set in the configuration."
                    )
                if datapoint.interface == Interfaces.FILE and not self.interfaces.file:
                    raise InterfaceNotActive(
                        f"The FILE interface is used for the {config_part} '{datapoint.id}', "
                        "but not set in the configuration."
                    )

        check_interface_active(self.inputs)
        check_interface_active(self.staticdata)
        check_interface_active(self.outputs)

        return self


class DataFileAttribute(BaseModel):
    """
    Model for data file attributes.

    Attributes:
        id (str): The unique identifier for the attribute.
        value (Union[str, float, int, bool, Dict, List, DataFrame, None]): \
            The value of the attribute.
        unit (Optional[DataUnits]): The unit of the attribute.
        time (Optional[str]): The timestamp of the attribute as a string.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    value: str | float | int | bool | dict | list | pd.DataFrame | None
    unit: DataUnits | None = None
    time: str | None = None


class DataFileEntity(BaseModel):
    """
    Model for data file entities.

    Attributes:
        id (str): The unique identifier for the entity.
        attributes (list[DataFileAttribute]): The attributes of the entity.
    """

    id: str
    attributes: list[DataFileAttribute]


class DataFile(BaseModel):
    """
    Model for static data files.

    Attributes:
        data (list[DataFileEntity]): The data entities.
    """

    data: list[DataFileEntity]


class FileStorageMethod(Enum):
    """
    Enum for the file storage method.
    """

    OVERWRITE = "overwrite"
    APPEND = "append"
    NEW_FILE = "new_file"
