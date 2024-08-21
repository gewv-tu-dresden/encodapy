# Description: This file contains the error handling classes for the system controller.
# Author: Martin Altenburger


class ConfigError(Exception):
    """Exception raised for errors in the configuration file.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class NotSupportedError(Exception):
    """Exception raised for a configuration which is not suported yet.

    Attributes:
        message -- explanation of the error
    """

    def __init__(
        self,
        message: str = "The configuration is not supported yet. Please contact the developer for further information.",
    ):
        self.message = message
        super().__init__(self.message)
