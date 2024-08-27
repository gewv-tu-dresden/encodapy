# Description: Default values for environment variables of the service
# Authors: Martin Altenburger
from enum import Enum


class DefaultEnvVariables(Enum):
    """
    Default environment variables for service
    """

    CONFIG_PATH = "./config.json"
    CB_URL = "http://localhost:1026"
    FIWARE_SERVICE = "service"
    FIWARE_SERVICE_PATH = "/"
    FIWARE_AUTH = False
    CRATE_DB_URL = "http://localhost:4200"
    CRATE_DB_USER = "crate"
    CRATE_DB_PW = ""
    CRATE_DB_SSL = False
    LOG_LEVEL = "WARNING"

    PATH_OF_INPUT_FILE = "./config/Input_file.csv"
