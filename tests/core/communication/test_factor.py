"""Tests for the optional `factor` key on attributes (Issue #92).

This module tests the central scaling helper `apply_factor` and the
application of the attribute `factor` in all communication connections
(MQTT, FILE, FIWARE) in both directions (input and output), including
timeseries (DataFrame) attributes.

Test Strategy:
- Unit tests for the helper with numeric, non-numeric and timeseries values
- Unit tests for the MQTT output payload scaling (plain, template and
  FIWARE_ATTR format)
- Unit test for the MQTT input data scaling (message store)
- Unit tests for the FILE input scaling (CSV value, CSV timeseries, JSON)
- Unit test for the FILE output scaling (send_data_to_json_file)
- Unit tests for the FIWARE input scaling (value and CrateDB timeseries)
- Unit tests for the FIWARE output scaling (scalar and timeseries)
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name
import json
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest
from filip.models.base import DataType
from filip.models.ngsi_v2.context import ContextAttribute, ContextEntity
from loguru import logger as loguru_logger

from encodapy.config import (
    AttributeTypes,
    DataQueryTypes,
    Interfaces,
    MQTTFormatTypes,
)
from encodapy.config.models import AttributeModel, InputModel, OutputModel
from encodapy.config.mqtt_messages_template import MQTTTemplateConfig
from encodapy.service.communication.file_connection import FileConnection
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.service.communication.mqtt_connection import MqttConnection
from encodapy.utils.models import (
    FiwareDatapointParameter,
    MetaDataModel,
    apply_factor,
)
from encodapy.utils.units import DataUnits, TimeUnits


class TestApplyFactor:
    """Tests for the central apply_factor helper."""

    def test_numeric_value_is_scaled(self):
        """Numeric values are multiplied by the factor."""
        assert apply_factor(1234, 0.1) == 123.4

    def test_numpy_scalars_are_scaled(self):
        """NumPy scalars (e.g. from pandas) are multiplied by the factor."""
        assert apply_factor(np.int64(1000), 0.1) == 100.0
        assert apply_factor(np.float64(1000), 0.1) == 100.0

    def test_negative_factor(self):
        """Negative factors are supported."""
        assert apply_factor(10, -2) == -20

    def test_default_factor_one_is_identity(self):
        """Factor 1.0 (the default) returns the value unchanged."""
        assert apply_factor(42, 1.0) == 42

    def test_bool_is_not_scaled(self):
        """Booleans are returned unchanged (bool is a subclass of int)."""
        assert apply_factor(True, 0.1) is True

    def test_string_is_not_scaled(self):
        """String values are returned unchanged."""
        assert apply_factor("42.0 °C", 0.1) == "42.0 °C"

    def test_none_is_not_scaled(self):
        """None is returned unchanged."""
        assert apply_factor(None, 0.1) is None

    def test_dataframe_numeric_columns_are_scaled(self):
        """Numeric columns of a DataFrame are scaled, others are kept."""
        dataframe = pd.DataFrame({"value": [10, 20], "label": ["a", "b"]})
        scaled = apply_factor(dataframe, 0.1)
        assert scaled["value"].tolist() == pytest.approx([1.0, 2.0])
        assert scaled["label"].tolist() == ["a", "b"]
        assert dataframe["value"].tolist() == [10, 20]

    def test_series_is_scaled(self):
        """Numeric Series (timeseries) are scaled."""
        series = pd.Series([10, 20])
        assert apply_factor(series, 0.1).tolist() == pytest.approx([1.0, 2.0])

    def test_string_series_is_not_scaled(self):
        """Non-numeric Series are returned unchanged."""
        series = pd.Series(["a", "b"])
        assert apply_factor(series, 0.1).tolist() == ["a", "b"]


class TestMqttFactor:
    """Tests for the `factor` key applied in the MQTT connection."""

    def test_prepare_mqtt_payload_plain_with_factor(self):
        """PLAIN output payload is scaled by the attribute factor."""
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        attribute = AttributeModel(
            id="temperature",
            value=1000,
            mqtt_format=MQTTFormatTypes.PLAIN,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id_interface = "TestOutput:001"
        assert connection._prepare_mqtt_payload(entity, attribute) == 100.0

    def test_prepare_mqtt_payload_template_with_factor(self):
        """Template output payload receives the scaled value."""
        template = MQTTTemplateConfig.model_validate(
            {
                "topic": "{{mqtt_topic_prefix}}/{{output_entity}}/{{output_attribute}}",
                "payload": {"value": "{{output_value}}"},
            }
        )
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        attribute = AttributeModel(
            id="temperature",
            value=1000,
            mqtt_format=template,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id_interface = "TestOutput:001"
        assert "100.0" in connection._prepare_mqtt_payload(entity, attribute)

    def test_prepare_mqtt_payload_fiware_attr_with_factor(self):
        """FIWARE_ATTR output payload is scaled by the attribute factor."""
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        attribute = AttributeModel(
            id="temperature",
            id_interface="temperature",
            value=25,
            mqtt_format=MQTTFormatTypes.FIWARE_ATTR,
            factor=10.0,
        )
        entity = MagicMock()
        entity.id_interface = "TestOutput:001"
        payload = connection._prepare_mqtt_payload(entity, attribute)
        assert payload == {"temperature": 250.0}

    def test_get_data_from_mqtt_with_factor(self):
        """Incoming values are multiplied by the attribute factor."""
        connection = MqttConnection()
        connection.mqtt_params = MagicMock()
        connection.mqtt_params.topic_prefix = "test"
        connection.mqtt_message_store = {
            "test/TestInput:001/temperature": {
                "entity_id": "TestInput:001",
                "attribute_id": "temperature",
                "value": 1000,
                "unit": None,
                "timestamp": datetime(2025, 1, 1, tzinfo=UTC),
            }
        }
        attribute = AttributeModel(
            id="temperature",
            id_interface="temperature",
            value=None,
            factor=0.1,
        )
        entity = MagicMock()
        entity.id = "TestInput:001"
        entity.id_interface = "TestInput:001"
        entity.attributes = [attribute]
        result = connection.get_data_from_mqtt(method=MagicMock(), entity=entity)
        assert result.attributes[0].data == 100.0


class TestFileFactor:
    """Tests for the `factor` key applied in the FILE connection."""

    @staticmethod
    def _prepare_csv_connection(tmp_path):
        """Create a FileConnection with a mocked config and CSV input file."""
        connection = FileConnection()
        connection.file_params = MagicMock()
        connection.config = MagicMock()
        connection.config.controller_settings.time_settings.calculation.timestep = 1
        connection.config.controller_settings.time_settings.calculation.timestep_unit = TimeUnits.MINUTE
        csv_file = tmp_path / "input.csv"
        csv_file.write_text(
            "Time;temp_raw\n"
            "2024-01-15T10:00:00+00:00;1000\n"
            "2024-01-15T10:01:00+00:00;2000\n",
            encoding="utf-8",
        )
        connection.file_params.path_of_input_file = str(csv_file)
        return connection

    def test_get_data_from_csv_file_value_with_factor(self, tmp_path):
        """CSV input values are multiplied by the attribute factor."""
        connection = self._prepare_csv_connection(tmp_path)
        entity = InputModel(
            id="TestInput:001",
            interface=Interfaces.FILE,
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temp_raw",
                    type=AttributeTypes.VALUE,
                    factor=0.1,
                )
            ],
        )
        result = connection.get_data_from_csv_file(
            method=DataQueryTypes.CALCULATION, entity=entity
        )
        assert result.attributes[0].data == 100.0

    def test_get_data_from_csv_file_timeseries_with_factor(self, tmp_path):
        """CSV input timeseries are scaled by the attribute factor."""
        connection = self._prepare_csv_connection(tmp_path)
        entity = InputModel(
            id="TestInput:001",
            interface=Interfaces.FILE,
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temp_raw",
                    type=AttributeTypes.TIMESERIES,
                    factor=0.1,
                )
            ],
        )
        result = connection.get_data_from_csv_file(
            method=DataQueryTypes.CALCULATION, entity=entity
        )
        data = result.attributes[0].data
        assert isinstance(data, pd.DataFrame)
        assert data["temp_raw"].tolist() == pytest.approx([100.0, 200.0])

    def test_get_data_from_json_file_with_factor(self, tmp_path):
        """JSON input values are multiplied by the attribute factor."""
        connection = FileConnection()
        connection.file_params = MagicMock()
        input_file = tmp_path / "input.json"
        input_file.write_text(
            json.dumps(
                {
                    "inputdata": [
                        {
                            "id": "TestInput:001",
                            "attributes": [
                                {"id": "temp_raw", "value": 1000},
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        connection.file_params.path_of_input_file = str(input_file)
        entity = InputModel(
            id="TestInput:001",
            interface=Interfaces.FILE,
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temp_raw",
                    type=AttributeTypes.VALUE,
                    factor=0.1,
                )
            ],
        )
        result = connection.get_data_from_json_file(method=MagicMock(), entity=entity)
        assert result is not None
        assert result.attributes[0].data == 100.0

    def test_send_data_to_json_file_with_factor(self, tmp_path):
        """Output values written to JSON files are scaled by the factor."""
        connection = FileConnection()
        connection.file_params = MagicMock()
        connection.file_params.path_of_results = str(tmp_path)
        output_entity = MagicMock()
        output_entity.id = "test_entity"
        attribute = AttributeModel(
            id="result",
            id_interface="result",
            value=1000,
            factor=0.1,
        )
        connection.send_data_to_json_file(
            output_entity=output_entity,
            output_attributes=[attribute],
            output_commands=[],
        )
        output_file = os.path.join(tmp_path, "outputs_test_entity.json")
        assert os.path.exists(output_file)
        with open(output_file, encoding="utf-8") as file_handle:
            content = json.load(file_handle)
        assert content[0]["attributes"][0]["value"] == 100.0


class TestFiwareFactor:
    """Tests for the `factor` key applied in the FIWARE connection."""

    def test_get_data_from_fiware_value_with_factor(self):
        """Incoming FIWARE values are multiplied by the attribute factor."""
        connection = FiwareConnection()
        connection.cb_client = MagicMock()
        connection.cb_client.get_entity.return_value = MagicMock(type="TestEntity")
        connection.cb_client.get_entity_attributes.return_value = {
            "temp_raw": ContextAttribute(type=DataType.NUMBER, value=1000)
        }
        entity = InputModel(
            id="TestInput:001",
            interface=Interfaces.FIWARE,
            attributes=[
                AttributeModel(
                    id="temp",
                    id_interface="temp_raw",
                    type=AttributeTypes.VALUE,
                    factor=0.1,
                )
            ],
        )
        result = connection.get_data_from_fiware(
            method=DataQueryTypes.CALCULATION,
            entity=entity,
            timestamp_latest_output=None,
        )
        assert result is not None
        assert result.attributes[0].data == 100.0

    def test_get_data_from_database_with_factor(self):
        """Timeseries values from CrateDB are scaled by the attribute factor."""
        connection = FiwareConnection()
        connection.fiware_conn_params = MagicMock()
        connection.crate_db_client = MagicMock()
        connection.crate_db_client.get_data.return_value = pd.DataFrame(
            {"temp_raw": [1000.0, 2000.0]},
            index=pd.DatetimeIndex(
                ["2024-01-15 10:00:00", "2024-01-15 10:01:00"], tz="UTC"
            ),
        )
        connection._calculate_dates = MagicMock(
            return_value=("2024-01-15T09:00:00Z", "2024-01-15T11:00:00Z")
        )
        connection.config = MagicMock()
        connection.config.controller_settings.time_settings.calculation.timestep = 1
        connection.config.controller_settings.time_settings.calculation.timestep_unit = TimeUnits.MINUTE
        entity_attributes = {
            "temp": {
                "id_interface": "temp_raw",
                "factor": 0.1,
                "metadata": MetaDataModel(),
            }
        }
        result = connection.get_data_from_database(
            entity=ContextEntity(id="TestInput:001", type="TestEntity"),
            entity_attributes=entity_attributes,
            method=DataQueryTypes.CALCULATION,
            timestamp_latest_output=None,
        )
        assert len(result) == 1
        data = result[0].data
        assert isinstance(data, pd.DataFrame)
        assert data["temp"].tolist() == pytest.approx([100.0, 200.0])

    @pytest.mark.asyncio
    async def test_send_data_to_fiware_scalar_with_factor(self):
        """Scalar output values sent to FIWARE are scaled by the factor."""
        connection = FiwareConnection()
        connection.cb_client = MagicMock()
        mock_entity = MagicMock()
        mock_entity.id = "TestOutput:001"
        mock_entity.type = "TestOutput"
        connection.cb_client.get_entity.return_value = mock_entity
        connection.cb_client.get_entity_attributes.return_value = {
            "temp": ContextAttribute(type=DataType.NUMBER)
        }
        output_entity = OutputModel(
            id="test_output",
            interface=Interfaces.FIWARE,
            id_interface="TestOutput:001",
            attributes=[],
        )
        attribute = AttributeModel(
            id="temp",
            id_interface="temp",
            type=AttributeTypes.VALUE,
            value=25,
            factor=10.0,
        )
        await connection._send_data_to_fiware(
            output_entity=output_entity,
            output_attributes=[attribute],
            output_commands=[],
        )
        call = connection.cb_client.update_or_append_entity_attributes.call_args
        assert call.kwargs["attrs"][0].value == 250.0

    @pytest.mark.asyncio
    async def test_prepare_timeseries_for_fiware_with_factor(self):
        """Timeseries output values sent to FIWARE are scaled by the factor."""
        connection = FiwareConnection()
        connection._send_timeseries_to_fiware = AsyncMock()
        dataframe = pd.DataFrame(
            {"temp": [20.0, 21.0, 22.0]},
            index=pd.date_range("2024-01-15 10:00:00", periods=3, freq="10min"),
        )
        datapoint = FiwareDatapointParameter(
            entity=ContextEntity(id="TestOutput:001", type="TestOutput"),
            attribute=AttributeModel(
                id="temp",
                id_interface="temp",
                type=AttributeTypes.TIMESERIES,
                value=dataframe,
                factor=0.1,
            ),
            metadata=[],
        )
        attr = await connection.prepare_timeseries_for_fiware(
            fiware_datapoint=datapoint, datatype=DataType.NUMBER
        )
        assert attr.value == pytest.approx(2.2)
        sent = connection._send_timeseries_to_fiware.call_args.kwargs[
            "attrs_timeseries"
        ]
        assert [item.value for item in sent] == pytest.approx([2.0, 2.1])

    def test_adjust_units_for_fiware_warns_on_double_scaling(self):
        """Combining a unit conversion with a factor logs a warning."""
        connection = FiwareConnection()
        attribute = AttributeModel(
            id="power",
            id_interface="power",
            value=1000.0,
            unit=DataUnits.WTT,
            factor=0.1,
        )
        messages = []
        sink_id = loguru_logger.add(lambda message: messages.append(str(message)))
        try:
            connection._adjust_units_for_fiware(
                id_output_entity="boiler",
                attribute=attribute,
                fiware_unit=DataUnits.KWT,
            )
        finally:
            loguru_logger.remove(sink_id)
        assert any("double scaling" in message for message in messages)
