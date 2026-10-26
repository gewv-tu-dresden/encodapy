"""Tests for the datapoint models in encodapy.utils.datapoints."""

from datetime import datetime, timezone

import pandas as pd
import pytest
from pydantic import ValidationError

from encodapy.utils.datapoints import DataPointDatetime, DataPointTimeSeries


def _valid_series() -> pd.Series:
    """Create a valid time series with a DatetimeIndex and float values."""
    index = pd.DatetimeIndex(
        [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        ]
    )
    return pd.Series([1.0, 2.0], index=index)


def test_datapoint_timeseries_accepts_series_with_datetime_index() -> None:
    """A Series with DatetimeIndex and float values is accepted unchanged."""

    series = _valid_series()

    datapoint = DataPointTimeSeries(value=series)

    assert datapoint.value.equals(series)


def test_datapoint_timeseries_converts_dataframe_to_series() -> None:
    """A DataFrame passed via the value field is squeezed into a Series."""

    series = _valid_series()
    frame = series.to_frame(name="temperature")

    datapoint = DataPointTimeSeries(value=frame)

    assert isinstance(datapoint.value, pd.Series)
    assert datapoint.value.equals(series)


def test_datapoint_timeseries_rejects_series_without_datetime_index() -> None:
    """A Series without a DatetimeIndex is rejected."""

    series = pd.Series([1.0, 2.0])

    with pytest.raises(ValidationError, match="Series must have a DatetimeIndex"):
        DataPointTimeSeries(value=series)


def test_datapoint_timeseries_rejects_non_numeric_series() -> None:
    """A Series with non-numeric values is rejected."""

    index = pd.DatetimeIndex(
        [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        ]
    )
    series = pd.Series(["a", "b"], index=index)

    with pytest.raises(ValidationError, match="float or integer"):
        DataPointTimeSeries(value=series)


def test_datapoint_timeseries_accepts_integer_series() -> None:
    """Integer dtype series are valid time series values."""

    index = pd.DatetimeIndex(
        [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        ]
    )
    series = pd.Series([1, 2], index=index)

    datapoint = DataPointTimeSeries(value=series)

    assert list(datapoint.value) == [1, 2]


def test_datapoint_datetime_accepts_datetime_object() -> None:
    """A datetime object is accepted as value."""

    timestamp = datetime(2026, 1, 1, 12, 0, 0)

    datapoint = DataPointDatetime(value=timestamp)

    assert datapoint.value == timestamp


def test_datapoint_datetime_converts_iso_string() -> None:
    """An ISO formatted string is converted to a datetime object."""

    datapoint = DataPointDatetime(value="2026-01-01T12:00:00")

    assert datapoint.value == datetime(2026, 1, 1, 12, 0, 0)


def test_datapoint_datetime_rejects_invalid_string() -> None:
    """A string that is not in ISO format is rejected with the custom error."""

    with pytest.raises(ValidationError, match="ISO format"):
        DataPointDatetime(value="01.01.2026")


def test_datapoint_datetime_rejects_unsupported_type() -> None:
    """Values that are neither datetime nor string are rejected."""

    with pytest.raises(
        ValidationError, match="datetime object or a string in ISO format"
    ):
        DataPointDatetime(value=["2026-01-01T12:00:00"])


def test_datapoint_datetime_rejects_timestamp_number() -> None:
    """Numbers (e.g. epoch timestamps) are not accepted as datetime values.

    The validator only supports datetime objects and ISO-format strings,
    so pydantic's coercion of numbers to datetime is explicitly disabled.
    """

    with pytest.raises(
        ValidationError, match="datetime object or a string in ISO format"
    ):
        DataPointDatetime(value=1767225600)
