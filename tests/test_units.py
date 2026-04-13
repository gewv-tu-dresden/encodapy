import pandas as pd
import pytest

from encodapy.utils.units import (
    DataUnits,
    TimeUnits,
    adjust_unit_of_value,
    adjust_units,
    get_time_unit_seconds,
)


def test_adjust_unit_of_value_converts_seconds_to_minutes() -> None:
    adjusted_value = adjust_unit_of_value(
        value=120,
        unit_actual=DataUnits.SECOND,
        unit_target=DataUnits.MINUTE,
    )

    assert adjusted_value == pytest.approx(2.0)


def test_adjust_unit_of_value_handles_temperature_offset() -> None:
    adjusted_value = adjust_unit_of_value(
        value=0,
        unit_actual=DataUnits.DEGREECELSIUS,
        unit_target=DataUnits.KELVIN,
    )

    assert adjusted_value == pytest.approx(273.15)


def test_adjust_unit_of_value_raises_for_incompatible_units() -> None:
    with pytest.raises(ValueError, match="Incompatible units"):
        adjust_unit_of_value(
            value=1,
            unit_actual=DataUnits.WTT,
            unit_target=DataUnits.DEGREECELSIUS,
        )


def test_adjust_units_returns_none_for_non_convertible_string() -> None:
    adjusted_value = adjust_units(
        value="not-a-number",
        unit_actual=DataUnits.WTT,
        unit_target=DataUnits.KWT,
    )

    assert adjusted_value is None


def test_adjust_units_converts_series_and_dataframe_values() -> None:
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
    seconds = get_time_unit_seconds(time_unit)

    assert seconds == pytest.approx(expected_seconds)
