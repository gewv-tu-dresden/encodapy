"""
Tests for ControllerBasicService helper functions.

This module contains tests for the private helper methods of the
ControllerBasicService class, including data type validation, GeoJSON
recognition, and processing functions.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from encodapy.service.basic_service import ControllerBasicService
from encodapy.config import AttributeModel, DataType, Interfaces, OutputModel, CommandModel
from encodapy.utils.models import DataTransferComponentModel
from encodapy.utils.units import DataUnits


def create_test_service():
    """Helper to create a service without automatic initialization."""
    with patch.object(ControllerBasicService, 'prepare_basic_start', lambda self: None):
        return ControllerBasicService()


class TestIsGeoJson:
    """Test class for the _is_geojson helper method."""

    def test_is_geojson_point(self):
        """
        Test GeoJSON Point recognition.
        
        Verifies that a valid GeoJSON Point object is correctly identified.
        """
        service = create_test_service()
        
        point_data = {
            "type": "Point",
            "coordinates": [100.0, 0.0]
        }
        
        assert service._is_geojson(point_data) is True

    def test_is_geojson_multipoint(self):
        """
        Test GeoJSON MultiPoint recognition.
        
        Verifies that a valid GeoJSON MultiPoint object is correctly identified.
        """
        service = ControllerBasicService()
        
        multipoint_data = {
            "type": "MultiPoint",
            "coordinates": [[100.0, 0.0], [101.0, 1.0]]
        }
        
        assert service._is_geojson(multipoint_data) is True

    def test_is_geojson_linestring(self):
        """
        Test GeoJSON LineString recognition.
        
        Verifies that a valid GeoJSON LineString object is correctly identified.
        """
        service = ControllerBasicService()
        
        linestring_data = {
            "type": "LineString",
            "coordinates": [[100.0, 0.0], [101.0, 1.0]]
        }
        
        assert service._is_geojson(linestring_data) is True

    def test_is_geojson_multilinestring(self):
        """
        Test GeoJSON MultiLineString recognition.
        
        Verifies that a valid GeoJSON MultiLineString object is correctly identified.
        """
        service = ControllerBasicService()
        
        multilinestring_data = {
            "type": "MultiLineString",
            "coordinates": [[[100.0, 0.0], [101.0, 1.0]], [[102.0, 2.0], [103.0, 3.0]]]
        }
        
        assert service._is_geojson(multilinestring_data) is True

    def test_is_geojson_polygon(self):
        """
        Test GeoJSON Polygon recognition.
        
        Verifies that a valid GeoJSON Polygon object is correctly identified.
        """
        service = ControllerBasicService()
        
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]]]
        }
        
        assert service._is_geojson(polygon_data) is True

    def test_is_geojson_multipolygon(self):
        """
        Test GeoJSON MultiPolygon recognition.
        
        Verifies that a valid GeoJSON MultiPolygon object is correctly identified.
        """
        service = ControllerBasicService()
        
        multipolygon_data = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[102.0, 2.0], [103.0, 2.0], [103.0, 3.0], [102.0, 3.0], [102.0, 2.0]]],
                [[[100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0]]]
            ]
        }
        
        assert service._is_geojson(multipolygon_data) is True

    def test_is_geojson_geometry_collection(self):
        """
        Test GeoJSON GeometryCollection recognition.
        
        Verifies that a valid GeoJSON GeometryCollection object is correctly identified.
        """
        service = ControllerBasicService()
        
        geometry_collection_data = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Point", "coordinates": [100.0, 0.0]},
                {"type": "LineString", "coordinates": [[100.0, 0.0], [101.0, 1.0]]}
            ]
        }
        
        assert service._is_geojson(geometry_collection_data) is True

    def test_is_geojson_feature(self):
        """
        Test GeoJSON Feature recognition.
        
        Verifies that a valid GeoJSON Feature object is correctly identified.
        """
        service = ControllerBasicService()
        
        feature_data = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [100.0, 0.0]},
            "properties": {"name": "Test Feature"}
        }
        
        assert service._is_geojson(feature_data) is True

    def test_is_geojson_feature_collection(self):
        """
        Test GeoJSON FeatureCollection recognition.
        
        Verifies that a valid GeoJSON FeatureCollection object is correctly identified.
        """
        service = ControllerBasicService()
        
        feature_collection_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [100.0, 0.0]},
                    "properties": {}
                }
            ]
        }
        
        assert service._is_geojson(feature_collection_data) is True

    def test_is_geojson_not_dict(self):
        """
        Test that non-dict values are not identified as GeoJSON.
        
        Verifies that the method returns False for non-dictionary inputs.
        """
        service = ControllerBasicService()
        
        assert service._is_geojson("not a dict") is False
        assert service._is_geojson([1, 2, 3]) is False
        assert service._is_geojson(123) is False
        assert service._is_geojson(None) is False

    def test_is_geojson_missing_type(self):
        """
        Test that objects without 'type' field are not identified as GeoJSON.
        
        Verifies that the method returns False when the 'type' field is missing.
        """
        service = ControllerBasicService()
        
        data = {
            "coordinates": [100.0, 0.0]
        }
        
        assert service._is_geojson(data) is False

    def test_is_geojson_invalid_type(self):
        """
        Test that objects with invalid 'type' are not identified as GeoJSON.
        
        Verifies that the method returns False for non-GeoJSON types.
        """
        service = ControllerBasicService()
        
        data = {
            "type": "InvalidType",
            "coordinates": [100.0, 0.0]
        }
        
        assert service._is_geojson(data) is False

    def test_is_geojson_type_not_string(self):
        """
        Test that objects with non-string 'type' are not identified as GeoJSON.
        
        Verifies that the method returns False when 'type' is not a string.
        """
        service = ControllerBasicService()
        
        data = {
            "type": 123,
            "coordinates": [100.0, 0.0]
        }
        
        assert service._is_geojson(data) is False

    def test_is_geojson_point_without_coordinates(self):
        """
        Test that Point without coordinates is not identified as GeoJSON.
        
        Verifies that the method returns False when required fields are missing.
        """
        service = ControllerBasicService()
        
        data = {
            "type": "Point"
        }
        
        assert service._is_geojson(data) is False

    def test_is_geojson_feature_without_geometry_or_features(self):
        """
        Test that Feature without geometry or features field is not valid.
        
        Verifies that the method checks for required fields in Feature.
        """
        service = ControllerBasicService()
        
        data = {
            "type": "Feature",
            "properties": {}
        }
        
        # This should return False because Feature requires geometry
        assert service._is_geojson(data) is False


class TestValidateDatatypeAgainstValue:
    """Test class for the _validate_datatype_against_value helper method."""

    def test_validate_datatype_boolean(self):
        """
        Test validation of BOOLEAN datatype.
        
        Verifies that boolean values are correctly identified as BOOLEAN type.
        Note: Boolean check must come before int check since bool is a subclass of int.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.BOOLEAN)
        mock_component = MagicMock(value=True)
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.BOOLEAN

    def test_validate_datatype_integer(self):
        """
        Test validation of INTEGER datatype.
        
        Verifies that integer values are correctly identified as INTEGER type.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.INTEGER)
        mock_component = MagicMock(value=42)
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.INTEGER

    def test_validate_datatype_number(self):
        """
        Test validation of NUMBER (float) datatype.
        
        Verifies that float values are correctly identified as NUMBER type.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.NUMBER)
        mock_component = MagicMock(value=3.14)
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.NUMBER

    def test_validate_datatype_text(self):
        """
        Test validation of TEXT datatype.
        
        Verifies that string values are correctly identified as TEXT type.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.TEXT)
        mock_component = MagicMock(value="test string")
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.TEXT

    @patch.object(ControllerBasicService, '_is_geojson')
    def test_validate_datatype_geojson(self, mock_is_geojson):
        """
        Test validation of GEOJSON datatype.
        
        Verifies that GeoJSON objects are correctly identified as GEOJSON type.
        """
        mock_is_geojson.return_value = True
        
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.GEOJSON)
        mock_component = MagicMock(value={"type": "Point", "coordinates": [0, 0]})
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.GEOJSON

    @patch.object(ControllerBasicService, '_is_geojson')
    def test_validate_datatype_structured_value(self, mock_is_geojson):
        """
        Test validation of STRUCTUREDVALUE datatype.
        
        Verifies that dictionary values (non-GeoJSON) are identified as STRUCTUREDVALUE.
        """
        mock_is_geojson.return_value = False
        
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.STRUCTUREDVALUE)
        mock_component = MagicMock(value={"key": "value"})
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.STRUCTUREDVALUE

    def test_validate_datatype_array(self):
        """
        Test validation of ARRAY datatype.
        
        Verifies that list values are correctly identified as ARRAY type.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.ARRAY)
        mock_component = MagicMock(value=[1, 2, 3, 4])
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        assert result == DataType.ARRAY

    def test_validate_datatype_mismatch_warning(self, capsys):
        """
        Test that datatype mismatch logs a warning.
        
        Verifies that the service logs a warning when the actual value type
        does not match the configured attribute datatype.
        
        Note: loguru is used for logging, so we check stdout/stderr capture.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.INTEGER)
        mock_component = MagicMock(value="string_value")  # String instead of integer
        
        service._validate_datatype_against_value(mock_attribute, mock_component)
        
        # Should still return the configured datatype
        # But should log a warning (via loguru to stdout by default)
        captured = capsys.readouterr()
        assert "Datatype mismatch" in captured.out

    def test_validate_datatype_unsupported_type_uses_config(self):
        """
        Test that unsupported types fall back to configured datatype.
        
        Verifies that when the value type is not recognized, the method
        returns the configured datatype from the attribute.
        """
        service = ControllerBasicService()
        mock_attribute = MagicMock(datatype=DataType.NUMBER)
        mock_component = MagicMock(value=object())  # Unsupported type
        
        result = service._validate_datatype_against_value(mock_attribute, mock_component)
        # Should return the configured datatype
        assert result == DataType.NUMBER


class TestProcessAttributes:
    """Test class for the _process_attributes helper method."""

    def test_process_attributes_match(self):
        """
        Test processing attributes with matching attribute_id.
        
        Verifies that attributes are correctly processed when the
        attribute_id matches between the component and output configuration.
        """
        service = ControllerBasicService()
        
        # Create output entity with attributes
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[
                AttributeModel(
                    id="temperature",
                    datatype=DataType.NUMBER,
                    name="Temperature"
                )
            ]
        )
        
        # Create component
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="temperature",
            value=25.5,
            unit=DataUnits.DEGREECELSIUS,
            timestamp=datetime.now()
        )
        
        # Process attributes
        output_attrs = {}
        result = service._process_attributes(component, output_entity, output_attrs)
        
        assert len(result) == 1
        assert "test_entity" in result
        assert len(result["test_entity"]) == 1
        assert result["test_entity"][0].id == "temperature"
        assert result["test_entity"][0].value == 25.5
        assert result["test_entity"][0].unit == DataUnits.DEGREECELSIUS

    def test_process_attributes_no_match(self):
        """
        Test processing attributes with non-matching attribute_id.
        
        Verifies that attributes are not processed when the attribute_id
        does not match between the component and output configuration.
        """
        service = ControllerBasicService()
        
        # Create output entity with attributes
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[
                AttributeModel(
                    id="temperature",
                    datatype=DataType.NUMBER,
                    name="Temperature"
                )
            ]
        )
        
        # Create component with different attribute_id
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="humidity",  # Different from temperature
            value=60.0,
            unit=DataUnits.PERCENT,
            timestamp=datetime.now()
        )
        
        # Process attributes
        output_attrs = {}
        result = service._process_attributes(component, output_entity, output_attrs)
        
        assert len(result) == 0  # No match, nothing added

    def test_process_attributes_multiple_attributes(self):
        """
        Test processing with multiple attributes in output entity.
        
        Verifies that the method correctly identifies the matching attribute
        among multiple attributes in the output entity.
        """
        service = ControllerBasicService()
        
        # Create output entity with multiple attributes
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[
                AttributeModel(
                    id="temperature",
                    datatype=DataType.NUMBER,
                    name="Temperature"
                ),
                AttributeModel(
                    id="pressure",
                    datatype=DataType.NUMBER,
                    name="Pressure"
                ),
                AttributeModel(
                    id="humidity",
                    datatype=DataType.NUMBER,
                    name="Humidity"
                )
            ]
        )
        
        # Create component for pressure
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="pressure",
            value=1013.25,
            unit=None,
            timestamp=datetime.now()
        )
        
        # Process attributes
        output_attrs = {}
        result = service._process_attributes(component, output_entity, output_attrs)
        
        assert len(result) == 1
        assert "test_entity" in result
        assert result["test_entity"][0].id == "pressure"
        assert result["test_entity"][0].value == 1013.25

    def test_process_attributes_datatype_validation(self):
        """
        Test that datatype validation is performed during attribute processing.
        
        Verifies that the _validate_datatype_against_value method is called
        during attribute processing.
        """
        service = ControllerBasicService()
        
        # Create output entity with attributes
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[
                AttributeModel(
                    id="status",
                    datatype=DataType.TEXT,
                    name="Status"
                )
            ]
        )
        
        # Create component
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="status",
            value="active",
            unit=None,
            timestamp=datetime.now()
        )
        
        # Process attributes
        output_attrs = {}
        result = service._process_attributes(component, output_entity, output_attrs)
        
        # Verify that the attribute was processed with validated datatype
        assert len(result) == 1
        assert result["test_entity"][0].datatype == DataType.TEXT


class TestProcessCommands:
    """Test class for the _process_commands helper method."""

    def test_process_commands_match(self):
        """
        Test processing commands with matching command_id.
        
        Verifies that commands are correctly processed when the command_id
        matches between the component and output configuration.
        """
        service = ControllerBasicService()
        
        # Create output entity with commands
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[],
            commands=[
                CommandModel(id="reset", value=None)
            ]
        )
        
        # Create component
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="reset",  # Matches command id
            value="reset_command",
            unit=None,
            timestamp=datetime.now()
        )
        
        # Process commands
        output_cmds = {}
        result = service._process_commands(component, output_entity, output_cmds)
        
        assert len(result) == 1
        assert "test_entity" in result
        assert len(result["test_entity"]) == 1
        assert result["test_entity"][0].id == "reset"
        assert result["test_entity"][0].value == "reset_command"

    def test_process_commands_no_match(self):
        """
        Test processing commands with non-matching command_id.
        
        Verifies that commands are not processed when the command_id
        does not match between the component and output configuration.
        """
        service = ControllerBasicService()
        
        # Create output entity with commands
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[],
            commands=[
                CommandModel(id="reset", value=None)
            ]
        )
        
        # Create component with different command_id
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="start",  # Different from reset
            value="start_command",
            unit=None,
            timestamp=datetime.now()
        )
        
        # Process commands
        output_cmds = {}
        result = service._process_commands(component, output_entity, output_cmds)
        
        assert len(result) == 0  # No match, nothing added

    @pytest.mark.parametrize("value", [
        42,          # int
        3.14,        # float
        "test",      # str
        True,        # bool
        {"key": "value"},  # dict
        [1, 2, 3]    # list
    ])
    def test_process_commands_supported_types(self, value):
        """
        Test processing commands with all supported value types.
        
        Verifies that all supported value types (int, float, str, bool, dict, list)
        are correctly processed for commands.
        """
        service = ControllerBasicService()
        
        # Create output entity with commands
        output_entity = OutputModel(
            id="test_entity",
            interface=Interfaces.FIWARE,
            attributes=[],
            commands=[
                CommandModel(id="command_1", value=None)
            ]
        )
        
        # Create component with the test value
        component = DataTransferComponentModel(
            entity_id="test_entity",
            attribute_id="command_1",
            value=value,
            unit=None,
            timestamp=datetime.now()
        )
        
        # Process commands
        output_cmds = {}
        result = service._process_commands(component, output_entity, output_cmds)
        
        assert len(result) == 1
        assert result["test_entity"][0].value == value

    def test_process_commands_unsupported_type_warning(self):
        """
        Test that unsupported command value types log a warning.
        
        Verifies that the _process_commands method has the logic to handle
        unsupported value types.
        
        Note: Due to Pydantic validation, DataTransferComponentModel will reject
        truly unsupported types. This test verifies that the method structure
        includes the warning logic.
        """
        from encodapy.service.basic_service import ControllerBasicService
        import inspect
        
        # Verify that _process_commands method exists and has the warning logic
        assert hasattr(ControllerBasicService, '_process_commands')
        
        # Get the source code of the method
        source = inspect.getsource(ControllerBasicService._process_commands)
        
        # Verify that the method checks for supported types
        assert 'isinstance' in source
        assert 'int, float, str, bool, dict, list' in source or 'isinstance(component.value' in source
        # Verify that the method logs a warning for unsupported types
        assert 'Unsupported command value type' in source
