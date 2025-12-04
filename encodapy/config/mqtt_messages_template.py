"""
Description: MQTT message templates - individual formats for MQTT messages
Author: Martin Altenburger
"""

import json
import os
from datetime import datetime
from typing import Any, Optional, Union

from jinja2 import Template
from loguru import logger
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import model_validator

from encodapy.config.types import MQTTFormatTypes
from encodapy.utils.error_handling import ConfigError


class MQTTTemplateConfig(BaseModel):
    """
    Model for MQTT template configuration.

    Loads and validates MQTT topic and payload templates from environment variables / \
        file as dictionary. Templates support the following placeholders:

        - ``__OUTPUT_ENTITY__``: The entity ID of the output.
        - ``__OUTPUT_ATTRIBUTE__``: The attribute ID of the output.
        - ``__OUTPUT_VALUE__``: The value of the output.
        - ``__OUTPUT_UNIT__``: The unit of the output.
        - ``__OUTPUT_TIME__``: The timestamp of the output.
        - ``__MQTT_TOPIC_PREFIX__``: The MQTT topic prefix from environment variables.

    The dictionary to build the templates can be provided in three ways:

        1. As a dictionary directly to the model.
        2. Via an environment variable `MQTT_TEMPLATE_<NAME>` as a string.
        3. Via a file path stored in an environment variable `MQTT_TEMPLATE_<NAME>`.

    The evironment variable `MQTT_TEMPLATE_<NAME>` (or variables for multiple templates) \
        must be set, where `<NAME>` is the name of the template to load.\
            It isn't loaded automatically from a `.env` file. 
    The dictionary must contain the keys `topic` and `payload`, and could look like this:

    .. code-block:: json

        {
            "topic": "sensors/__OUTPUT_ENTITY__/__OUTPUT_ATTRIBUTE__",
            "payload": {
                "value": "__OUTPUT_VALUE__",
                "info_dict": {
                    "output_entity": "__OUTPUT_ENTITY__",
                    "output_attribute": "__OUTPUT_ATTRIBUTE__",
                    "output_time": "__OUTPUT_TIME__"
                }
            }
            "time_format": "%Y-%m-%dT%H:%M%z"
        }

    The key `time_format` is optional, as default '%Y-%m-%dT%H:%M:%S%z' is used.

    Please see the examples for this.

    Arguments:
        topic (Template): The Jinja2 template for the MQTT topic.
        payload (Template): The Jinja2 template for the MQTT payload.
        time_format (str): The format string for the timestamp in the payload. \
            Refer to Python's datetime.strptime documentation for more details.

    Raises:
        ValueError: If the input is invalid or templates cannot be loaded.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    topic: Template
    payload: Template
    time_format: str = "%Y-%m-%dT%H:%M:%S%z"

    @model_validator(mode="before")
    @classmethod
    def load_mqtt_message_template(
        cls, mqtt_format_template_env: Union[str, dict]
    ) -> Any:
        """
        Load the MQTT message template from an environment variable or dictionary.

        Args:
            mqtt_format_template_env: Either a string (environment variable name) or a dictionary
                                      containing `topic` and `payload` templates and `time_format`
                                      for the timestamp information.

        Returns:
            dict: A dictionary with `topic` and `payload` as `jinja2.Template` objects.

        Raises:
            ValueError: If the input is invalid or templates cannot be loaded.
        """

        if isinstance(mqtt_format_template_env, dict):
            return cls._handle_dict_input(mqtt_format_template_env)
        if not isinstance(mqtt_format_template_env, str):
            raise ValueError(
                "Invalid type for mqtt_format_template_env: "
                f"{type(mqtt_format_template_env).__name__}. "
                "Expected a string or dict."
            )

        if mqtt_format_template_env in [member.value for member in MQTTFormatTypes]:
            # return as predefined template in MQTTFormatTypes, should not be handled here
            raise ValueError(
                f"MQTT format '{mqtt_format_template_env}' is a predefined format "
                "and cannot be used as a template."
            )
        env_variable = f"MQTT_{mqtt_format_template_env.upper()}"
        mqtt_format_template_info = os.getenv(env_variable)

        mqtt_format_template: Optional[dict] = None
        if mqtt_format_template_info is not None:
            if mqtt_format_template_info.endswith(".json"):
                try:
                    with open(mqtt_format_template_info, "r", encoding="utf-8") as file:
                        mqtt_format_template = json.load(file)
                except (FileNotFoundError, json.JSONDecodeError):
                    logger.error(
                        f"MQTT template file {mqtt_format_template_info} "
                        "not found or invalid."
                    )
                    mqtt_format_template = None

            else:
                try:
                    mqtt_format_template = json.loads(mqtt_format_template_info)
                except json.JSONDecodeError:
                    logger.error("MQTT template string is not a valid JSON.")
                    mqtt_format_template = None
        else:
            logger.error(
                f"Environment variable {env_variable} "
                f"for the mqtt-template '{mqtt_format_template_env}' not found."
            )

        if not isinstance(mqtt_format_template, dict):
            raise ValueError(
                "Invalid MQTT template: expected a dict, "
                f"got {type(mqtt_format_template).__name__} ({mqtt_format_template})."
            )

        return {
            "topic": cls.load_mqtt_template(
                template_raw=mqtt_format_template, part="topic"
            ),
            "payload": cls.load_mqtt_template(
                template_raw=mqtt_format_template, part="payload"
            ),
            "time_format": cls._handle_time_format(mqtt_format_template),
        }

    @classmethod
    def _handle_time_format(cls, mqtt_format_template: dict) -> str:
        """
        Validate and process the time format.

        Args:
            mqtt_format_template (dict): Dictionary containing the time format (`time_format` key).
        Returns:
            str: The validated time format string.
        """
        time_format = mqtt_format_template.get("time_format", "%Y-%m-%dT%H:%M:%S%z")

        if not isinstance(time_format, str):
            raise ConfigError(
                "Invalid time_format in mqtt template: expected a str, "
                f"got {type(time_format).__name__} ({time_format})."
            )
        try:
            datetime.now().strftime(time_format)
        except (ValueError, TypeError) as e:
            raise ConfigError(
                f"Invalid time format string '{time_format}': {str(e)}"
            ) from e

        return time_format

    @classmethod
    def _handle_dict_input(cls, mqtt_format_data: dict) -> dict:
        """
        Validate and process dictionary input for MQTT templates.

        Args:
            mqtt_format_data: Dictionary containing `topic` and `payload` templates.
                            Each template can be a `str` or `dict`.

        Returns:
            dict: Processed templates for `topic` and `payload`.

        Raises:
            ValueError: If `mqtt_format_data` is missing `topic` or `payload` keys.
        """
        if not isinstance(mqtt_format_data, dict):
            raise ValueError("Input data must be a dictionary.")

        if "topic" not in mqtt_format_data:
            raise ValueError("MQTT template dict must contain 'topic' key.")
        if "payload" not in mqtt_format_data:
            raise ValueError("MQTT template dict must contain 'payload' key.")

        return {
            "topic": cls.load_mqtt_template(
                template_raw=mqtt_format_data, part="topic"
            ),
            "payload": cls.load_mqtt_template(
                template_raw=mqtt_format_data, part="payload"
            ),
            "time_format": cls._handle_time_format(mqtt_format_data),
        }

    @classmethod
    def load_mqtt_template(cls, template_raw: dict, part: str) -> Template:
        """
        Process a raw template string or dictionary into a `jinja2.Template`.

        Args:
            template_raw: Raw template data (str or dict).
            part: Either "topic" or "payload".

        Returns:
            Template: The rendered Jinja2 template.

        Raises:
            ValueError: If the template format is invalid.
        """
        template_raw = template_raw.get(part, {})
        if isinstance(template_raw, dict):
            template = json.dumps(template_raw)
        elif isinstance(template_raw, str):
            template = template_raw
        else:
            raise ValueError("Invalid template format. Must be dict or str.")

        parameters = [
            "__OUTPUT_ENTITY__",
            "__OUTPUT_ATTRIBUTE__",
            "__OUTPUT_VALUE__",
            "__OUTPUT_UNIT__",
            "__OUTPUT_TIME__",
            "__MQTT_TOPIC_PREFIX__",
        ]
        for param in parameters:
            if param in template:
                if param == "__MQTT_TOPIC_PREFIX__":
                    prefix = os.getenv("MQTT_TOPIC_PREFIX", "")
                    if prefix == "":
                        prefix_with_slash = ""
                    elif not prefix.endswith("/"):
                        prefix_with_slash = prefix + "/"
                    else:
                        prefix_with_slash = prefix
                    template = template.replace(param + "/", prefix_with_slash)
                    template = template.replace(param, prefix)
                else:
                    clean_name = param.strip("_").lower()
                    template = template.replace(param, f"{{{{{clean_name}}}}}")

            else:
                logger.debug(
                    f"Parameter {param} not found in payload template for {part}."
                )

        return Template(template)


class MQTTTemplateConfigDoc(BaseModel):
    """
    Model for MQTT template configuration.

    **Mock class for documentation purposes.**
    
    Note:
        In the actual implementation, `topic` and `payload` are `jinja2.Template` objects,
        `time_format` is a `str` as time format for the timestamp in the payload.
        This mock uses `dict` to avoid import issues during documentation generation.
        
        For more information,\
            see :class:`~encodapy.config.mqtt_messages_template.MQTTTemplateConfig`.
    """

    topic: dict
    payload: dict
    time_format: str = "%Y-%m-%dT%H:%M:%S%z"
