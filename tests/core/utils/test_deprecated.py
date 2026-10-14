"""Tests for encodapy.utils.deprecated module."""

import pytest

from encodapy.utils.deprecated import deprecated


@deprecated("Use new_function instead.")
def sample_function(value: int) -> int:
    """Sample function decorated as deprecated."""
    return value * 2


def test_deprecated_decorator_emits_warning_and_returns_result() -> None:
    """Calling a deprecated function warns and still returns its result."""

    with pytest.warns(DeprecationWarning, match="sample_function is deprecated"):
        result = sample_function(21)

    assert result == 42


def test_deprecated_decorator_keeps_function_metadata() -> None:
    """The decorator preserves the wrapped function metadata."""

    assert sample_function.__name__ == "sample_function"
