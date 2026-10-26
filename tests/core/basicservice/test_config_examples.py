"""
Tests for loading configuration from example files.
"""


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

    def test_config_from_example_01_has_correct_entity_ids(
        self, config_from_example_01
    ):
        """Test that the example config has the expected entity IDs."""
        assert config_from_example_01.inputs[0].id == "input_fiware_01"
        assert config_from_example_01.inputs[0].id_interface == "urn:input_fiware:01"
        assert config_from_example_01.outputs[0].id == "storage_calculation"
        assert (
            config_from_example_01.outputs[0].id_interface
            == "urn:storage_calculation:01"
        )

    def test_config_from_example_01_has_correct_attributes(
        self, config_from_example_01
    ):
        """Test that the example config has the expected attributes."""
        input_entity = config_from_example_01.inputs[0]
        assert len(input_entity.attributes) == 2
        assert input_entity.attributes[0].id == "temperature_1"
        assert input_entity.attributes[1].id == "temperature_2"

    def test_config_from_example_01_time_settings(self, config_from_example_01):
        """Test that the example config has the expected time settings."""
        from encodapy.utils.units import TimeUnits

        time_settings = config_from_example_01.time_settings
        assert time_settings is not None
        assert time_settings.calculation is not None
        assert time_settings.calculation.timerange == 24
        assert time_settings.calculation.timerange_unit == TimeUnits.HOUR


class TestDeprecatedConfigMigration:
    """Test migration of deprecated configuration keys (issue #80)."""

    def _base_config(self) -> dict:
        """Return a minimal valid configuration without time settings."""
        return {
            "interfaces": {"fiware": True},
            "inputs": [],
            "outputs": [],
            "staticdata": [],
            "controller_components": [],
        }

    def _build_config_with_logs(self, **kwargs) -> tuple:
        """Build a ConfigModel and capture the emitted loguru warnings.

        Returns:
            tuple: The ConfigModel and the joined warning messages.
        """
        import loguru

        from encodapy.config.models import ConfigModel

        messages: list = []
        handler_id = loguru.logger.add(
            lambda m: messages.append(str(m)), level="WARNING"
        )
        try:
            config = ConfigModel(**self._base_config(), **kwargs)
        finally:
            loguru.logger.remove(handler_id)
        return config, "\n".join(messages)

    def test_controller_settings_is_migrated(self):
        """Test that the deprecated 'controller_settings' key is migrated."""
        config, logs = self._build_config_with_logs(
            controller_settings={
                "time_settings": {
                    "calculation": {"timerange": 24, "timerange_unit": "hour"}
                }
            },
        )
        assert config.time_settings.calculation.timerange == 24
        assert "'controller_settings' is deprecated" in logs

    def test_specific_settings_are_dropped(self):
        """Test that deprecated 'specific_settings' are dropped with a warning."""
        config, logs = self._build_config_with_logs(
            controller_settings={
                "time_settings": {
                    "calculation": {"timerange": 24, "timerange_unit": "hour"}
                },
                "specific_settings": {"unused": True},
            },
        )
        assert not hasattr(config, "specific_settings")
        assert "'specific_settings' is deprecated" in logs

    def test_empty_specific_settings_are_dropped_with_warning(self):
        """Test that an empty deprecated 'specific_settings' key is warned about."""
        _, logs = self._build_config_with_logs(
            controller_settings={
                "time_settings": {
                    "calculation": {"timerange": 24, "timerange_unit": "hour"}
                },
                "specific_settings": {},
            },
        )
        assert "'specific_settings' is deprecated" in logs

    def test_results_in_time_settings_are_dropped(self):
        """Test that deprecated time settings 'results' are dropped with a warning."""
        config, logs = self._build_config_with_logs(
            time_settings={
                "calculation": {"timerange": 24, "timerange_unit": "hour"},
                "results": {"timestep": 1},
            },
        )
        assert not hasattr(config.time_settings, "results")
        assert "'results' in the time settings is deprecated" in logs

    def test_new_format_without_warnings(self):
        """Test that the new format is accepted without deprecation warnings."""
        config, logs = self._build_config_with_logs(
            time_settings={"calculation": {"timerange": 24, "timerange_unit": "hour"}},
        )
        assert config.time_settings.calculation.timerange == 24
        assert "deprecated" not in logs
