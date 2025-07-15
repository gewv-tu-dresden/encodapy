"""
Modules for defining mediums used in thermal energy systems.
Author: Martin Altenburger
"""
from enum import Enum
from pydantic import BaseModel

class Medium(Enum):
    """
    Enum class for the mediums
    """
    WATER = "water"

class MediumParameters(BaseModel):
    """
    Base class for the medium parameters
    """
    cp: float
    rho: float

MEDIUM_VALUES = {
    Medium.WATER: MediumParameters(cp = 4.19, rho = 997)
    }

def get_medium_parameter(
    medium:Medium
    )-> MediumParameters:
    """Function to get the medium parameter

    Args:
        medium (Mediums): The medium

    Returns:
        float: Parameter of the medium
    """

    return MEDIUM_VALUES[medium]
