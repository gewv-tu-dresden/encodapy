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


def get_medium_parameter(
    medium: Medium, temperature: Optional[float] = None
) -> MediumParameters:
    """Function to get the medium parameter
       - const values, if no temperature is set
       - calculation of cp and rho (constant pressure) as approximation of Glück
           - https://berndglueck.de/stoffwerte.php
           - "Zustandswerte Luft Wasser Dampf"  ISBN 3-345-00487-9

    Args:
        medium (Mediums): The medium
        temperature : float = None

    Returns:
        MediumParameters: The parameters of the medium
    """
    if medium not in MEDIUM_VALUES:
        logger.error(f"Medium {medium} not available")
        raise ValueError(f"Medium {medium} not available")

    if temperature is None:
        return MEDIUM_VALUES[medium]

    if medium is Medium.WATER:
        if temperature <= 0.1:
            logger.error("Attention! Temperature to low!")
            values = MediumParameters(cp=None, rho=None)
        elif temperature > 99.0:
            logger.error("Attention! Temperature to hight!")
            values = MediumParameters(cp=None, rho=None)
        else:
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
            values = MediumParameters(cp=cp_calc, rho=rho_calc)

        return values
    # TODO add more mediums
    logger.error("Medium is not supported for temperature calculation")
    raise ValueError("Medium is not supported for temperature calculation")
