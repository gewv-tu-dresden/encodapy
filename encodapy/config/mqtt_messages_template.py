"""
Description: MQTT message templates - indivuidual formats for MQTT messages
Author: Martin Altenbruger
"""
from typing import Any
import os
from jinja2 import Template
import json
from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import model_validator
from loguru import logger


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
    def load_mqtt_message_template(cls, mqtt_format_template_env: str) -> Any:
        """
        Load the MQTT message template from the environment variable.
        """
        if not isinstance(mqtt_format_template_env, str):
            return None
        env_variable = f"MQTT_{mqtt_format_template_env.upper()}"
        mqtt_format_template_info = os.getenv(env_variable)
        if mqtt_format_template_info is None:
            return None
        
        if ".json" in mqtt_format_template_info:
            try:
                with open(mqtt_format_template_info, "r", encoding="utf-8") as file:
                    mqtt_format_template = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                logger.error(f"MQTT template file {mqtt_format_template_info} not found or invalid.")
                return None
            
        else:
            try:
                mqtt_format_template = json.loads(mqtt_format_template_info)
            except json.JSONDecodeError:
                logger.error("MQTT template string is not a valid JSON.")
                return None

        if not isinstance(mqtt_format_template, dict):
            return None

        return {
            "topic": cls.load_mqtt_template(
                template_raw=mqtt_format_template,
                part="topic"
            ),
            "payload": cls.load_mqtt_template(
                template_raw=mqtt_format_template,
                part="payload"
            )
        }

    @classmethod
    def load_mqtt_template(cls,
                           template_raw:dict,
                           part:str
                           ) -> Template:
        """
        Get the MQTT payload / topic template.
        Template for the MQTT message could be used for formatting and \
            possible values are:
            - __OUTPUT_ENTITY__: The entity ID of the output from the component configuration.
            - __OUTPUT_ATTRIBUTE__: The attribute ID of the output from the component configuration.
            - __OUTPUT_VALUE__: The value of the output from the calculation.
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

        parameters = ["__OUTPUT_ENTITY__", "__OUTPUT_ATTRIBUTE__", "__OUTPUT_VALUE__", "__OUTPUT_UNIT__", "__OUTPUT_TIME__"]
        for param in parameters:
            if param in template:
                clean_name = param.strip("_").lower()
                template = template.replace(
                    param,
                    f"{{{{{clean_name}}}}}"
                )

            else:
                logger.debug(f"Parameter {param} not found in payload template for {part}.")

        return Template(template)
