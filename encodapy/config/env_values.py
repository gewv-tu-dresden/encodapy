"""
This module contains the environment variables for the communication interfaces.
Authors: Martin Altenburger, Paul Seidel, Maximilian Beyer
more information: https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage
"""

from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BasicEnvVariables(BaseSettings):
    """
    Basic environment variables for the service.
    They are automatically loaded from the environment or a .env file.
    """

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_prefix="", case_sensitive=False
    )

    config_path: str = Field(
        default="config.json", description="Path to the configuration file"
    )
    log_level: str = Field(
        default="WARNING", description="Logging level for the service"
    )
    reload_staticdata: bool = Field(
        default=False,
        description="If true, static data will be reloaded at each time step",
    )
    start_hold_time: Optional[float] = Field(
        default=0.0, description="Time in seconds to hold the start of the service"
    )


class FiwareEnvVariables(BaseSettings):
    """
    Environment variables for FIWARE communication.
    They are automatically loaded from the environment or a .env file.

    Environment variables always have the prefix `FIWARE_`.
    """

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_prefix="FIWARE_", case_sensitive=False
    )

    auth: bool = Field(
        default=False,
        description="Enables authentication for FIWARE requests",
    )
    client_id: Optional[str] = Field(
        default=None, description="Client ID for FIWARE authentication"
    )
    client_pw: Optional[str] = Field(
        default=None, description="Client password for FIWARE authentication"
    )
    token_url: Optional[AnyHttpUrl] = Field(
        default=None, description="Token URL for FIWARE authentication"
    )
    bearer_token: Optional[str] = Field(
        default=None, description="Bearer token for FIWARE authentication"
    )
    cb_url: Optional[AnyHttpUrl] = Field(
        default=AnyHttpUrl("http://localhost:1026"),
        description="URL of the Context Broker (e.g., Orion-LD)",
    )
    service: str = Field(..., description="FIWARE Service header for tenant isolation")
    service_path: str = Field(
        default="/", description="FIWARE Service Path for sub-tenant isolation"
    )

    crate_db_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:4200"),
        description="URL of the CrateDB instance",
    )
    crate_db_user: str = Field(default="crate", description="Username for CrateDB")
    crate_db_pw: str = Field(
        default="", description="Password for CrateDB (empty = no authentication)"
    )
    crate_db_ssl: bool = Field(
        default=False, description="Enables SSL for the connection to CrateDB"
    )


class MQTTEnvVariables(BaseSettings):
    """
    MQTT environment variables for the service.
    They are automatically loaded from the environment or a .env file.

    Environment variables always have the prefix `MQTT_`.
    """

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_prefix="MQTT_", case_sensitive=False
    )

    host: str = Field(
        default="localhost", description="Hostname or IP address of the MQTT broker"
    )
    port: int = Field(default=1883, description="Port number of the MQTT broker")
    username: Optional[str] = Field(
        default="", description="Username for MQTT broker authentication"
    )
    password: Optional[str] = Field(
        default="", description="Password for MQTT broker authentication"
    )
    topic_prefix: str = Field(
        default="", description="Prefix for all MQTT topics used by the service"
    )
    timestamp_key: str = Field(
        default="TimeInstant",
        description=(
            "Key name in the MQTT message payload that contains the timestamp. "
            "Examples: 'TimeInstant' (default), 'timestamp', 'time'. "
            "If the key is not present in the payload, "
            "the timestamp of the MQTT message receipt will be used."
        ),
    )


class FileEnvVariables(BaseSettings):
    """
    File environment variables for the service.
    They are automatically loaded from the environment or a .env file.

    Environment variables always have the prefix `FILE_`.
    """

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", env_prefix="FILE_", case_sensitive=False
    )

    path_of_input_file: str = Field(
        default="./input/input_file.csv", description="Path to the input CSV file"
    )
    path_of_static_data: str = Field(
        default="./input/static_data.json",
        description="Path to the static data JSON file",
    )
    path_of_results: str = Field(
        default="./results", description="Directory path to store the results"
    )

    time_format_fie : str = Field(
        default="%Y-%m-%d %H:%M:%SZ",
        description="""Time format of the date_time column in the input file.
        It needs to be compatible with the strptime format codes
        (https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes)""",
    )
    start_time_file: str = Field(
        default="2025-01-01 00:00",
        description="""Start time for processing data from the input file.
        It needs to be ISO compatible
        (https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat)""",
    )
