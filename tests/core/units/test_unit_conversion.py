"""Tests for unit conversion helpers and time-unit normalization."""

import pandas as pd
import pytest

from encodapy.utils import units as units_module
from encodapy.utils.units import (
    DataUnits,
    TimeUnits,
    adjust_unit_of_value,
    adjust_units,
    get_time_unit_seconds,
    get_unit_adjustment_factor,
)


def test_adjust_unit_of_value_converts_seconds_to_minutes() -> None:
    """Second-to-minute conversion returns the expected numeric factor."""

    adjusted_value = adjust_unit_of_value(
        value=120,
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value == pytest.approx(2.0)


def test_adjust_unit_of_value_handles_temperature_offset() -> None:
    """Temperature conversion applies additive offsets correctly."""

    adjusted_value = adjust_unit_of_value(
        value=0,
        unit_actual=DataUnits.DEGREECELSIUS,
        unit_target=DataUnits.KELVIN,
    )

    assert adjusted_value == pytest.approx(273.15)


def test_adjust_unit_of_value_raises_for_incompatible_units() -> None:
    """Incompatible dimensions raise a ValueError."""

    with pytest.raises(ValueError, match="Incompatible units"):
        adjust_unit_of_value(
            value=1,
            unit_actual=DataUnits.WTT,
            unit_target=DataUnits.DEGREECELSIUS,
        )


def test_adjust_units_returns_none_for_non_convertible_string() -> None:
    """Non-numeric scalar input returns None instead of raising."""

    adjusted_value = adjust_units(
        value="not-a-number",
        unit_actual=DataUnits.WTT,
        unit_target=DataUnits.KWT,
    )

    assert adjusted_value is None


def test_adjust_units_converts_series_and_dataframe_values() -> None:
    """Vectorized conversions work for both Series and DataFrame inputs."""

    values = pd.Series([60.0, 120.0])
    adjusted_series = adjust_units(
        value=values,
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    frame = pd.DataFrame({"value": [60.0, 120.0]})
    adjusted_frame = adjust_units(
        value=frame,
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
        column_name="value",
    )

    assert adjusted_series is not None
    assert list(adjusted_series) == pytest.approx([1.0, 2.0])
    assert adjusted_frame is not None
    assert list(adjusted_frame["value"]) == pytest.approx([1.0, 2.0])


@pytest.mark.parametrize(
    ("time_unit", "expected_seconds"),
    [
        (TimeUnits.MINUTE, 60.0),
        (DataUnits.HOUR, 3600.0),
        ("day", 86400.0),
    ],
)
def test_get_time_unit_seconds(
    time_unit: TimeUnits | DataUnits | str, expected_seconds: float
) -> None:
    """Known time units resolve to their corresponding number of seconds."""

    seconds = get_time_unit_seconds(time_unit)

    assert seconds == pytest.approx(expected_seconds)


@pytest.mark.parametrize(
    ("unit_actual", "unit_target", "expected"),
    [
        (DataUnits.KWT, DataUnits.KWT, 1.0),
        (DataUnits.WTT, DataUnits.KWT, 0.001),
        (DataUnits.SECOND, DataUnits.MINUTE, 1 / 60),
    ],
)
def test_get_unit_adjustment_factor_converts_units(
    unit_actual: DataUnits, unit_target: DataUnits, expected: float
) -> None:
    """The deprecated helper still returns correct adjustment factors."""

    with pytest.warns(DeprecationWarning, match="get_unit_adjustment_factor"):
        factor = get_unit_adjustment_factor(
            unit_actual=unit_actual, unit_target=unit_target
        )

    assert factor == pytest.approx(expected)


@pytest.mark.parametrize(
    ("unit_actual", "unit_target"),
    [
        (None, DataUnits.KWT),
        (DataUnits.KWT, None),
        (DataUnits.DEGREECELSIUS, DataUnits.KELVIN),
        (DataUnits.WTT, DataUnits.DEGREECELSIUS),
    ],
)
def test_get_unit_adjustment_factor_returns_none_for_invalid_cases(
    unit_actual: "DataUnits | None", unit_target: "DataUnits | None"
) -> None:
    """None units, temperature units and incompatible units yield None."""

    with pytest.warns(DeprecationWarning, match="get_unit_adjustment_factor"):
        factor = get_unit_adjustment_factor(
            unit_actual=unit_actual, unit_target=unit_target
        )

    assert factor is None


def test_adjust_unit_of_value_raises_for_non_numeric_value() -> None:
    """Non-numeric values are rejected with a ValueError."""

    with pytest.raises(ValueError, match="float or int"):
        adjust_unit_of_value(
            value="120",  # type: ignore[arg-type]
            unit_actual=DataUnits.SECOND,
            unit_target=DataUnits.MINUTE,
        )


def test_adjust_units_returns_input_when_units_are_equal() -> None:
    """Equal actual and target units return the value unchanged."""

    adjusted_value = adjust_units(
        value="unchanged",
        unit_actual=DataUnits.KWT,
        unit_target=DataUnits.KWT,
    )

    assert adjusted_value == "unchanged"


def test_adjust_units_returns_none_for_bool_value() -> None:
    """Boolean values cannot be unit adjusted and return None."""

    adjusted_value = adjust_units(
        value=True,
        unit_actual=DataUnits.WTT,
        unit_target=DataUnits.KWT,
    )

    assert adjusted_value is None


def test_adjust_units_converts_scalar_value() -> None:
    """Scalar numeric values are converted directly."""

    adjusted_value = adjust_units(
        value=120,
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value == pytest.approx(2.0)


def test_adjust_units_converts_list_values() -> None:
    """Each entry of a list is converted separately."""

    adjusted_value = adjust_units(
        value=[60.0, 120.0],
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value == pytest.approx([1.0, 2.0])


def test_adjust_units_converts_dict_values() -> None:
    """Each entry of a dict is converted separately."""

    adjusted_value = adjust_units(
        value={"a": 60.0, "b": 120.0},
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value == pytest.approx({"a": 1.0, "b": 2.0})


def test_adjust_units_returns_none_for_dict_with_non_numeric_value() -> None:
    """A dict containing a non-numeric value returns None."""

    adjusted_value = adjust_units(
        value={"a": 60.0, "b": "invalid"},
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value is None


@pytest.mark.parametrize(
    ("value", "unit_actual", "unit_target"),
    [
        (None, DataUnits.WTT, DataUnits.KWT),
        (10.0, None, DataUnits.KWT),
        (10.0, DataUnits.WTT, None),
    ],
)
def test_adjust_units_returns_none_for_none_inputs(
    value: "float | None",
    unit_actual: "DataUnits | None",
    unit_target: "DataUnits | None",
) -> None:
    """None value or units result in None instead of an exception."""

    adjusted_value = adjust_units(
        value=value, unit_actual=unit_actual, unit_target=unit_target
    )

    assert adjusted_value is None


def test_adjust_units_returns_none_for_unsupported_type() -> None:
    """Value types without a conversion branch return None."""

    adjusted_value = adjust_units(
        value=(60.0, 120.0),
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value is None


@pytest.mark.parametrize(
    "time_unit",
    [
        "not-a-unit",
        "watt",
        42,
    ],
)
def test_get_time_unit_seconds_returns_none_for_invalid_input(
    time_unit: "str | int",
) -> None:
    """Undefined units, non-time units and invalid types yield None."""

    seconds = get_time_unit_seconds(time_unit)  # type: ignore[arg-type]

    assert seconds is None


def test_adjust_unit_of_value_with_equal_units_returns_value_unchanged() -> None:
    """Equal actual and target units return the value unchanged."""

    adjusted_value = adjust_unit_of_value(
        value=42,
        unit_actual=DataUnits.KWT,
        unit_target=DataUnits.KWT,
    )

    assert adjusted_value == 42


def test_adjust_unit_of_value_raises_when_unit_mapping_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing unit mapping raises a ValueError after logging a warning."""

    monkeypatch.delitem(units_module._UNIT_MAP, DataUnits.KWT)  # pylint: disable=protected-access

    with pytest.raises(ValueError, match="Unit mapping missing"):
        adjust_unit_of_value(
            value=1.0,
            unit_actual=DataUnits.KWT,
            unit_target=DataUnits.WTT,
        )


def test_get_unit_adjustment_factor_returns_none_when_unit_mapping_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing unit mapping in the deprecated helper yields None."""

    monkeypatch.delitem(units_module._UNIT_MAP, DataUnits.KWT)  # pylint: disable=protected-access

    with pytest.warns(DeprecationWarning, match="get_unit_adjustment_factor"):
        factor = get_unit_adjustment_factor(
            unit_actual=DataUnits.KWT, unit_target=DataUnits.WTT
        )

    assert factor is None
