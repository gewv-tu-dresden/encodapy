"""
Modules for defining mediums used in thermal energy systems.
Author: Martin Altenburger, Paul Seidel
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel
from loguru import logger


class Medium(Enum):
    """
    Enum class for the mediums

    TODO: Add more mediums
    """

    WATER = "water"


class MediumParameters(BaseModel):
    """
    Base class for the medium parameters

    Attributes:
        cp (float): Specific heat capacity [kJ/kgK]
        rho (float): Density [kg/m³]
    """

    cp: float
    rho: float


MEDIUM_VALUES = {Medium.WATER: MediumParameters(cp=4.19, rho=997)}

# Supported temperature range for the temperature-dependent calculation of water
# parameters based on the Glück approximation [degree Celsius]
WATER_TEMPERATURE_MIN = 0.1
WATER_TEMPERATURE_MAX = 99.0
# The Glück approximation is only reasonably accurate from this temperature
# upward [degree Celsius]; below it the results should be treated with care
WATER_ACCURATE_TEMPERATURE_MIN = 10.0


def get_medium_parameter(
    medium: Medium, temperature: Optional[float] = None
) -> MediumParameters:
    """Function to get the medium parameter
       - const values, if no temperature is set
       - calculation of cp and rho (constant pressure) as approximation of Glück
           - https://berndglueck.de/stoffwerte.php
           - "Zustandswerte Luft Wasser Dampf"  ISBN 3-345-00487-9

       The Glück approximation is only reasonably accurate from around
       10 degree Celsius upward. Temperatures between
       WATER_TEMPERATURE_MIN and WATER_ACCURATE_TEMPERATURE_MIN are still
       calculated, but a warning is logged and the results should be treated
       with care. A property library like CoolProp could provide reliable
       calculations across a wider range of temperatures and media.

    Args:
        medium (Mediums): The medium
        temperature : float = None

    Returns:
        MediumParameters: The parameters of the medium

    Raises:
        ValueError: If the medium is not available, the temperature is outside
            the supported range (WATER_TEMPERATURE_MIN to
            WATER_TEMPERATURE_MAX degree Celsius for water) or the
            medium does not support temperature-dependent calculations
    """
    if medium not in MEDIUM_VALUES:
        logger.error(f"Medium {medium} not available")
        raise ValueError(f"Medium {medium} not available")

    if temperature is None:
        return MEDIUM_VALUES[medium]

    if medium is Medium.WATER:
        if temperature < WATER_TEMPERATURE_MIN:
            logger.error("Attention! Temperature to low!")
            raise ValueError(
                f"Temperature of {temperature} degree Celsius is too low "
                "to calculate medium parameters for water"
            )
        if temperature > WATER_TEMPERATURE_MAX:
            logger.error("Attention! Temperature to hight!")
            raise ValueError(
                f"Temperature of {temperature} degree Celsius is too high "
                "to calculate medium parameters for water"
            )
        if temperature < WATER_ACCURATE_TEMPERATURE_MIN:
            logger.warning(
                f"Temperature of {temperature} degree Celsius is below "
                f"{WATER_ACCURATE_TEMPERATURE_MIN} degree Celsius; the Glück "
                "approximation is only reasonably accurate from around "
                f"{WATER_ACCURATE_TEMPERATURE_MIN} degree Celsius upward"
            )

        # rho aproximation of Glück [kg/m³]:
        rho_calc = (
            1.002045 * 1000
            - 1.029905 * 0.1 * temperature
            - 3.698162 * 0.001 * temperature**2
            + 3.991053 * 0.000001 * temperature**3
        )
        # cp aproximation of Glück [kJ/kgK]:
        cp_calc = (
            4.177375
            - 2.144614 * 0.000001 * temperature
            - 3.165823 * 0.0000001 * temperature**2
            + 4.134309 * 0.00000001 * temperature**3
        )
        return MediumParameters(cp=cp_calc, rho=rho_calc)
    # TODO add more mediums
    logger.error("Medium is not supported for temperature calculation")
    raise ValueError("Medium is not supported for temperature calculation")
