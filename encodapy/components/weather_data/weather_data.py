"""
Defines the OpenWeatherMapData class.
Author: Paul Seidel
"""

from typing import Optional, Union

from loguru import logger

from encodapy.components.basic_component import BasicComponent, StaticDataEntityModel
from encodapy.config.models import ControllerComponentModel
from encodapy.utils.datapoints import DataPointNumber
from encodapy.utils.units import DataUnits

from .weather_data_config import (
    WeatherDataConfigData,
    WeatherDataInputData,
    WeatherDataOutputData,
)


class WeatherData(BasicComponent):
    """
    Class for the OpenWeatherMap component
    """

    def __init__(
        self,
        config: Union[ControllerComponentModel, list[ControllerComponentModel]],
        component_id: str,
        static_data: Optional[list[StaticDataEntityModel]] = None,
    ) -> None:
        # Add the necessary instance variables here
        self.example_variable: float = 1

        # Add the type declaration for the following variables so that autofill works properly
        self.config_data: WeatherDataConfigData
        self.input_data: WeatherDataInputData
        self.output_data: WeatherDataOutputData

        # Prepare Basic Parts / needs to be the latest part
        super().__init__(
            config=config, component_id=component_id, static_data=static_data
        )

        # Component-specific initialization logic

    def prepare_component(self) -> None:
        """
        Prepare the component (e.g., initialize resources)
        """
        logger.debug("Hello from WeatherData! Preparing...")

    def calculate_a_result(self) -> DataPointNumber:
        """
        Example calculation function for the WeatherData component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating a_result in WeatherData...")
        a_number = 42.0

        return DataPointNumber(value=a_number, unit=DataUnits.DEGREECELSIUS)

    def calculate_another_result(self) -> DataPointNumber:
        """
        Example calculation function for the WeatherData component
        """
        # Example calculation logic using the input data stored in the component
        logger.debug("Calculating another_result in WeatherData...")
        another_number = (
            42
            if self.input_data.another_number_input.value is None
            else self.input_data.another_number_input.value
        )
        return DataPointNumber(value=another_number, unit=DataUnits.DEGREECELSIUS)

    def calculate(self) -> None:
        """
        Perform the calculations for the WeatherData component
        """
        logger.debug("Calculating in WeatherData...")

        self.output_data = WeatherDataOutputData(
            t_ambient=self.calculate_a_result(),
        )
