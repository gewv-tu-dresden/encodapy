"""Tests for encodapy.utils.mediums module."""

import pytest

from encodapy.utils import mediums
from encodapy.utils.mediums import Medium, MediumParameters, get_medium_parameter


def test_get_medium_parameter_without_temperature_returns_constant_values() -> None:
    """Without a temperature the predefined constant parameters are returned."""

    parameters = get_medium_parameter(medium=Medium.WATER)

    assert parameters == MediumParameters(cp=4.19, rho=997)


def test_get_medium_parameter_with_temperature_calculates_approximation() -> None:
    """Temperatures within the valid range use the Glück approximation."""

    parameters = get_medium_parameter(medium=Medium.WATER, temperature=50.0)

    # Reference values computed from the approximation formulas
    assert parameters.cp == pytest.approx(4.1816441998)
    assert parameters.rho == pytest.approx(988.148951625)


def test_get_medium_parameter_with_temperature_too_low_raises() -> None:
    """Temperatures below the valid range raise a ValueError."""

    with pytest.raises(ValueError, match="too low"):
        get_medium_parameter(medium=Medium.WATER, temperature=0.05)


def test_get_medium_parameter_with_temperature_too_high_raises() -> None:
    """Temperatures above the valid range raise a ValueError."""

    with pytest.raises(ValueError, match="too high"):
        get_medium_parameter(medium=Medium.WATER, temperature=100.0)


def test_get_medium_parameter_with_boundary_temperatures_is_calculated() -> None:
    """The range boundaries (0.1 and 99.0 degree Celsius) are still valid."""

    lower = get_medium_parameter(medium=Medium.WATER, temperature=0.2)
    upper = get_medium_parameter(medium=Medium.WATER, temperature=99.0)

    assert lower.cp > 0
    assert upper.cp > 0


def test_get_medium_parameter_with_unknown_medium_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A medium without stored parameters raises a ValueError."""

    monkeypatch.delitem(mediums.MEDIUM_VALUES, Medium.WATER)

    with pytest.raises(ValueError, match="not available"):
        get_medium_parameter(medium=Medium.WATER)
