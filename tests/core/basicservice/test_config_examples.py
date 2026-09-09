"""
Tests for loading configuration from example files.
"""

import pytest


class TestConfigFromExamples:
    """Test configuration loading from example files."""

    def test_config_from_example_01_loaded(self, config_from_example_01):
        """Test that config_from_example_01 fixture loads correctly."""
        assert config_from_example_01 is not None
        assert config_from_example_01.interfaces.fiware is True
        assert config_from_example_01.interfaces.mqtt is False
        assert config_from_example_01.interfaces.file is False
        assert len(config_from_example_01.inputs) == 1
        assert len(config_from_example_01.outputs) == 1
        assert len(config_from_example_01.staticdata) == 1
        assert len(config_from_example_01.controller_components) == 1


    def test_config_from_example_01_has_correct_entity_ids(self, config_from_example_01):
        """Test that the example config has the expected entity IDs."""
        assert config_from_example_01.inputs[0].id == "input_fiware_01"
        assert config_from_example_01.inputs[0].id_interface == "urn:input_fiware:01"
        assert config_from_example_01.outputs[0].id == "storage_calculation"
        assert config_from_example_01.outputs[0].id_interface == "urn:storage_calculation:01"

    def test_config_from_example_01_has_correct_attributes(self, config_from_example_01):
        """Test that the example config has the expected attributes."""
        input_entity = config_from_example_01.inputs[0]
        assert len(input_entity.attributes) == 2
        assert input_entity.attributes[0].id == "temperature_1"
        assert input_entity.attributes[1].id == "temperature_2"

    def test_config_from_example_01_time_settings(self, config_from_example_01):
        """Test that the example config has the expected time settings."""
        from encodapy.utils.units import TimeUnits
        
        time_settings = config_from_example_01.controller_settings.time_settings
        assert time_settings is not None
        assert time_settings.calculation is not None
        assert time_settings.calculation.timerange == 24
        assert time_settings.calculation.timerange_unit == TimeUnits.HOUR
