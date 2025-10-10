"""
Description: This file contains the models for the configuration of the system controller.
Authors: Martin Altenburger
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, ValidationError, Field
from pydantic.functional_validators import model_validator
from loguru import logger
from pandas import DataFrame
from filip.models.base import DataType
from encodapy.config.types import (
    AttributeTypes,
    Interfaces,
    TimerangeTypes,
    MQTTFormatTypes,
)
from encodapy.utils.error_handling import ConfigError, InterfaceNotActive
from encodapy.utils.units import DataUnits, TimeUnits
from encodapy.components.basic_component_config import ControllerComponentModel
from encodapy.config.mqtt_messages_template import MQTTTemplateConfig


class InterfaceModel(BaseModel):
    """
    Base class for the interfaces
    """

    mqtt: bool = False
    fiware: bool = False
    file: bool = False

class AttributeModel(BaseModel):
    """
    Base class for the attributes

    Contains:
    - id: The id of the attribute
    - id_interface: The id of the attribute on the interface (if not set, the id is used)
    - type: The type of the attribute
    - value: The value of the attribute
    - unit: The unit of the attribute
    - datatype: The datatype of the attribute
    - timestamp: The timestamp of the attribute
    - mqtt_format: The format of the attribute for MQTT \
        (if not set, the default format is used) - only for mqtt interface needed

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = Field(default=None)
    type: AttributeTypes = AttributeTypes.VALUE
    value: Union[str, float, int, bool, Dict, List, DataFrame, None] = None
    unit: Union[DataUnits, None] = None
    datatype: DataType = DataType("Number")
    timestamp: Union[datetime, None] = None
    mqtt_format: Union[MQTTFormatTypes, MQTTTemplateConfig] = MQTTFormatTypes.PLAIN

    @model_validator(mode="after")
    def set_id_interface(self) -> "AttributeModel":
        """
        Sets the 'id_interface' attribute to the value of 'id' if it is currently None.

        Returns:
            AttributeModel: The instance with the updated 'id_interface' attribute.
        """
        if self.id_interface is None:
            self.id_interface = self.id
        return self
    @model_validator(mode="before")
    def check_mqtt_format(cls, data: Any) -> Any:
        """
        Checks the mqtt_format in the input data and the template configuration. if used.

        Args:
            data (Any): The input data to check.

        Returns:
            Any: The input data with the checked mqtt_format.
        """
        
        if "mqtt_format" not in data:
            pass
        elif not isinstance(data["mqtt_format"], str):
            error_message = "The mqtt_format should be a string of type MQTTFormatTypes"
            logger.error(error_message)
            raise ValueError(error_message)
        elif data["mqtt_format"].startswith(MQTTFormatTypes.TEMPLATE.value):
            env_variable = f"MQTT_{data['mqtt_format'].upper()}"
            if os.getenv(env_variable) is None:
                error_message = (
                    f"Environment variable '{env_variable}' is not set, "
                    "but needed for template mqtt_format"
                )
                logger.error(error_message)
                data["mqtt_format"] = None
                raise ValueError(error_message)
            #TODO Template Verification
            # data["mqtt_format"] = MQTTFormatTypes.TEMPLATE.value
        else:
            try:
                MQTTFormatTypes(data["mqtt_format"])
            except ValueError:
                logger.warning(
                    f"mqtt_format '{data['mqtt_format']}' is not valid - using default format 'plain'"
                )
                data["mqtt_format"] = MQTTFormatTypes.PLAIN.value
        return data


class CommandModel(BaseModel):
    """
    Base class for the commands

    Contains:
    - id: The id of the command
    - id_interface: The id of the command on the interface (if not set, the id is used)
    - value: The value of the command
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    id_interface: str = Field(default=None)
    value: Union[str, int, float, List, Dict, None] = None

    @model_validator(mode="after")
    def set_id_interface(self) -> "CommandModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface is None:
            self.id_interface = self.id
        return self


class InputModel(BaseModel):
    """
    Model for the configuration of inputs.

    Contains:
    - id: The id of the input
    - interface: The interface of the input
    - id_interface: The id of the input on the interface, default is the id
    - attributes: A list of attributes for the input as AttributeModel

    """

    id: str
    interface: Interfaces
    id_interface: str = Field(default=None)
    attributes: list[AttributeModel]

    @model_validator(mode="after")
    def set_id_interface(self) -> "InputModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface is None:
            self.id_interface = self.id
        return self


class StaticDataModel(InputModel):
    """
    Model for the configuration of inputs.

    Contains:
    - id: The id of the input
    - interface: The interface of the input
    - id_interface: The id of the input on the interface
    - attributes: A list of attributes for the static data as AttributeModel

    """


class OutputModel(BaseModel):
    """
    Model for the configuration of outputs.

    Contains:
    - id: The id of the output
    - interface: The interface of the output
    - id_interface: The id of the output on the interface, default is the id
    - attributes: The attributes of the output
    """

    id: str
    interface: Interfaces
    id_interface: str = Field(default=None)
    attributes: list[AttributeModel]
    commands: list[CommandModel] = []

    @model_validator(mode="after")
    def set_id_interface(self) -> "OutputModel":
        """Sets the 'id_interface' attribute to the value of 'id'
        if it is currently None.
        """
        if self.id_interface is None:
            self.id_interface = self.id
        return self


class TimeSettingsCalculationModel(BaseModel):
    """
    Base class for the calculation time settings of the controller / system.

    Contains:
    - timerange: The timerange for the calculation (if only one value is needed and primary value,
    otherwise use timerange_min and timerange_max)
    - timerange_min: The minimum timerange for the calculation (only used if timerange is not set
    and timerange_max is set too)
    - timerange_max: The maximum timerange for the calculation (only used if timerange is not set
    and timerange_min is set too)
    - timerange_type: Type of time period, relative to the last result or absolute at the current
    time (if not set, the default type is absolute)
    - timerange_unit: The unit of the timerange (if not set, the default unit is minute)
    - timestep: The timestep for the calculation (if not set, the default value is 1), the
    related unit is defined in the timestep_unit attribute
    - timestep_unit: The unit of the timestep (if not set, the default unit is second)
    - sampling_time: The sampling time for the calculation (if not set, the default value is 1),
    the related unit is defined in the sampling_time_unit attribute
    - sampling_time_unit: The unit of the sampling time (if not set, the default unit is minute)
    """

    timerange: Optional[float] = None
    timerange_min: Optional[float] = None
    timerange_max: Optional[float] = None
    timerange_type: Optional[TimerangeTypes] = TimerangeTypes.ABSOLUTE
    timerange_unit: Optional[TimeUnits] = TimeUnits.MINUTE

    timestep: Union[float, int] = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND

    sampling_time: Union[float, int] = 1
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

    Contains:
    - timerange: The timerange for the calibration (if not set, the default value is 1),
    the related unit is defined in the timerange_unit attribute
    - timerange_unit: The unit of the timerange (if not set, the default unit is minute)
    - timestep: The timestep for the calibration (if not set, the default value is 1),
    the related unit is defined in the timestep_unit attribute
    - timestep_unit: The unit of the timestep (if not set, the default unit is second)
    - sampling_time: The sampling time for the calibration (if not set, the default value is 1),
    the related unit is defined in the sampling_time_unit attribute
    - sampling_time_unit: The unit of the sampling time (if not set, the default unit is day)

    """

    timerange: Optional[float] = None
    timerange_unit: Optional[TimeUnits] = TimeUnits.MINUTE

    timestep: Union[float, int] = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND

    sampling_time: Union[float, int] = 1
    sampling_time_unit: TimeUnits = TimeUnits.DAY


class TimeSettingsResultsModel(BaseModel):
    """
    Settings for the timesteps of the results.
    """

    timestep: Union[float, int] = 1
    timestep_unit: TimeUnits = TimeUnits.SECOND


class TimeSettingsModel(BaseModel):
    """
    Base class for the time settings of the controller / system.

    Contains:
    - calculation: The timeranges and settings für the calculation
    - calibration: The timeranges and settings for the calibration
    - results: The timesettings for the results

    TODO: Add the needed fields - calibration?
    """

    calculation: TimeSettingsCalculationModel
    calibration: Optional[TimeSettingsCalibrationModel] = None
    results: Optional[TimeSettingsResultsModel] = None


class ControllerSettingModel(BaseModel):
    """
    Model for the configuration of the controller settings.

    Contains:
    - time_settings: The time settings for the controller
    - specific_settings: The specific settings for the controller - not defined as a model

    TODO: What is needed here?
    """

    time_settings: TimeSettingsModel
    specific_settings: Optional[dict] = {}


class ConfigModel(BaseModel):
    """
    Base Model for the configuration

    Contains:
    - interfaces: The interfaces of the system controller
    - inputs: The inputs of the system controller
    - outputs: The outputs of the system controller
    - staticdata: The static configuration data for devices the system controller
    - controller_components: The components of the controller
    - controller_settings: The settings for the controller
    """

    interfaces: InterfaceModel

    inputs: list[InputModel]
    outputs: list[OutputModel]
    staticdata: list[StaticDataModel]

    controller_components: list[ControllerComponentModel]

    controller_settings: ControllerSettingModel

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
            datapoints: Union[
                List[InputModel], List[StaticDataModel], List[OutputModel]
            ],
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
    
    Contains:
        id (str): The unique identifier for the attribute.
        value (Union[str, float, int, bool, Dict, List, DataFrame, None]): \
            The value of the attribute.
        unit (Optional[DataUnits]): The unit of the attribute.
        time (Optional[str]): The timestamp of the attribute as a string.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    value: Union[str, float, int, bool, Dict, List, DataFrame, None]
    unit: Optional[DataUnits] = None
    time: Optional[str] = None


class DataFileEntity(BaseModel):
    """
    Model for data file entities.

    Contains:
        id (str): The unique identifier for the entity.
        attributes (list[DataFileAttribute]): The attributes of the entity.
    """

    id: str
    attributes: list[DataFileAttribute]


class DataFile(BaseModel):
    """
    Model for static data files.

    Contains:
        data (list[DataFileEntity]): The data entities.
    """

    data: list[DataFileEntity]
