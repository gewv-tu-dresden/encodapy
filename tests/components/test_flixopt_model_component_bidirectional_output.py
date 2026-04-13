"""Unit tests for bidirectional substation output mapping in FlixoptModelComponent."""

from types import SimpleNamespace
import unittest
from typing import Any
from unittest.mock import patch

import pandas as pd

from encodapy.components.flixopt_model_component.flixopt_model_component import (
    FlixoptModelComponent,
)


class _TestableFlixoptModelComponent(FlixoptModelComponent):
    """Test helper exposing controlled setup hooks."""

    def set_bidirectional_substations(self, bidirectional_substations: Any) -> None:
        """Set bidirectional substations for isolated unit tests."""
        self._bidirectional_substations = bidirectional_substations


class TestFlixoptModelComponentBidirectionalOutput(unittest.TestCase):
    """Tests around bidirectional substation result aggregation."""

    def test_prepare_output_data_uses_forward_minus_reverse(self) -> None:
        """Bidirectional thermal power must be exported as forward minus reverse flow."""
        component: Any = _TestableFlixoptModelComponent.__new__(_TestableFlixoptModelComponent)

        time_index = pd.date_range("2026-01-01", periods=3, freq="h")
        all_timeseries = pd.DataFrame(
            {
                "sub_a_fwd(heat_bus)|flow_rate": [10.0, 5.0, 8.0],
                "sub_a_rev(heat_bus)|flow_rate": [3.0, 1.0, 5.0],
            },
            index=time_index,
        )

        converter = SimpleNamespace(label="sub_a", thermal_flow="heat_bus")
        setattr(
            component,
            "flixopt_model",
            SimpleNamespace(
                storages=[],
                converters=[converter],
                exchangers=[],
            ),
        )
        component.set_bidirectional_substations(
            {
                "sub_a": (
                    SimpleNamespace(label="sub_a_fwd"),
                    SimpleNamespace(label="sub_a_rev"),
                    1.0,
                    1.0,
                )
            }
        )

        with patch.object(
            FlixoptModelComponent,
            "export_results_as_timeseries",
            return_value=all_timeseries,
        ):
            component.prepare_output_data(results=SimpleNamespace(solution=None))

        output_series = getattr(component.output_data, "sub_a_thermal_power").value
        expected = pd.Series(
            [7.0, 4.0, 3.0],
            index=time_index,
            name="sub_a_thermal_power",
        )
        pd.testing.assert_series_equal(output_series, expected)


if __name__ == "__main__":
    unittest.main()
