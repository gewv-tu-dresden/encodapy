"""
Description: MQTT message templates - individual formats for MQTT messages
Author: Martin Altenburger
"""

import json
import os
from typing import Any, Union, Optional
from jinja2 import Template
from loguru import logger
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import model_validator
from encodapy.config.types import MQTTFormatTypes

class MQTTTemplateConfig(BaseModel):
    """
    Model for MQTT template configuration.

    Contains:
        topic (Template): The template for the MQTT topic.
        payload (Template): The template for the MQTT payload.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    topic: Template
    payload: Template

    @model_validator(mode="before")
    @classmethod
    def load_mqtt_message_template(cls, mqtt_format_template_env: Union[str, dict]) -> Any:
        """
        Load the MQTT message template from the environment variable.
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
            logger.error(f"Environment variable {env_variable} "
                         f"for the mqtt-template {mqtt_format_template_env} not found.")

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
        }

    @classmethod
    def _handle_dict_input(cls, mqtt_format_data: dict) -> dict:
        """
        Handle dictionary input for MQTT template.

        Args:
            mqtt_format_data (dict): The input data dictionary.
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
        }

    @classmethod
    def load_mqtt_template(cls, template_raw: dict, part: str) -> Template:
        """
        Get the MQTT payload / topic template.
        Template for the MQTT message could be used for formatting and \
            possible values are:
            - __OUTPUT_ENTITY__: The entity ID of the output from the component configuration.
            - __OUTPUT_ATTRIBUTE__: The attribute ID of the output from the component configuration.
            - __OUTPUT_VALUE__: The value of the output from the calculation.
            - __OUTPUT_UNIT__: The unit of the output from the calculation.
            - __OUTPUT_TIME__: The timestamp of the output from the calculation.

        Returns:
            Optional[Template]: The MQTT payload template or None if not defined.
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
                    if prefix != "" and not prefix.endswith("/"):
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
