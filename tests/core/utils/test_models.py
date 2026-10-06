"""Tests for the pydantic models in encodapy.utils.models."""

from datetime import datetime, timezone

import pandas as pd
import pytest
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import ContextEntity
from pydantic import ValidationError

from encodapy.config.models import AttributeModel, CommandModel
from encodapy.config.types import AttributeTypes
from encodapy.utils.models import (
    ComponentModel,
    DatabaseParameter,
    DataTransferComponentModel,
    DataTransferModel,
    FiwareAuth,
    FiwareConnectionParameter,
    FiwareDatapointParameter,
    FiwareParameter,
    InputDataAttributeModel,
    InputDataEntityModel,
    InputDataModel,
    MetaDataModel,
    OutputDataAttributeModel,
    OutputDataEntityModel,
    OutputDataModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import DataUnits

TIMESTAMP = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)


def make_input_attribute(
    value=None,
    attribute_id: str = "temperature_1",
    unit: DataUnits | None = None,
) -> InputDataAttributeModel:
    """Create a valid input data attribute model."""
    return InputDataAttributeModel(
        id=attribute_id,
        data=value,
        unit=unit,
        data_type=AttributeTypes.VALUE,
        data_available=True,
        latest_timestamp_input=TIMESTAMP,
    )


class TestInputDataModels:
    """Tests for the input data models."""

    @pytest.mark.parametrize(
        "value",
        [
            "text",
            1.5,
            3,
            True,
            {"key": "value"},
            [1, 2, 3],
            None,
        ],
    )
    def test_attribute_accepts_scalar_types(self, value) -> None:
        """The data field accepts all defined scalar and container types."""
        attribute = make_input_attribute(value=value)

        assert attribute.data == value
        assert attribute.data_type is AttributeTypes.VALUE
        assert attribute.data_available is True
        assert attribute.latest_timestamp_input == TIMESTAMP

    def test_attribute_accepts_dataframe(self) -> None:
        """The data field accepts a pandas DataFrame."""
        frame = pd.DataFrame({"temperature": [20.0, 21.0]})
        attribute = make_input_attribute(value=frame)

        assert isinstance(attribute.data, pd.DataFrame)
        pd.testing.assert_frame_equal(attribute.data, frame)

    def test_attribute_defaults(self) -> None:
        """The unit defaults to None if not set."""
        attribute = make_input_attribute(value=20.0)

        assert attribute.unit is None

    def test_attribute_requires_data_type(self) -> None:
        """A missing data_type raises a ValidationError."""
        with pytest.raises(ValidationError):
            InputDataAttributeModel(  # type: ignore[call-arg]
                id="temperature_1",
                data=20.0,
                data_available=True,
                latest_timestamp_input=None,
            )

    def test_attribute_rejects_invalid_data_type(self) -> None:
        """An unknown data type string raises a ValidationError."""
        with pytest.raises(ValidationError):
            InputDataAttributeModel(
                id="temperature_1",
                data=20.0,
                data_type="invalid",
                data_available=True,
                latest_timestamp_input=None,
            )

    def test_input_entity_holds_attributes(self) -> None:
        """An input entity groups a list of input data attributes."""
        entity = InputDataEntityModel(
            id="thermal_storage",
            attributes=[
                make_input_attribute(value=20.0, unit=DataUnits.DEGREECELSIUS),
                make_input_attribute(value=30.0, attribute_id="temperature_2"),
            ],
        )

        assert entity.id == "thermal_storage"
        assert len(entity.attributes) == 2
        assert entity.attributes[0].unit is DataUnits.DEGREECELSIUS

    def test_static_data_entity_is_input_entity(self) -> None:
        """The static data entity model inherits from the input entity model."""
        entity = StaticDataEntityModel(
            id="static",
            attributes=[make_input_attribute(value=5.0)],
        )

        assert isinstance(entity, InputDataEntityModel)

    def test_input_data_model_groups_entities(self) -> None:
        """The input data model holds input, output and static entities."""
        input_entity = InputDataEntityModel(
            id="input", attributes=[make_input_attribute(value=1.0)]
        )
        output_entity = OutputDataEntityModel(id="output")
        static_entity = StaticDataEntityModel(
            id="static", attributes=[make_input_attribute(value=2.0)]
        )
        model = InputDataModel(
            input_entities=[input_entity],
            output_entities=[output_entity],
            static_entities=[static_entity],
        )

        assert model.input_entities[0].id == "input"
        assert model.output_entities[0].id == "output"
        assert model.static_entities[0].id == "static"


class TestOutputDataModels:
    """Tests for the output data models."""

    def test_output_attribute_defaults(self) -> None:
        """The latest output timestamp defaults to None."""
        attribute = OutputDataAttributeModel(id="storage__level")

        assert attribute.latest_timestamp_output is None

    def test_output_attribute_with_timestamp(self) -> None:
        """The latest output timestamp can be set."""
        attribute = OutputDataAttributeModel(
            id="storage__level", latest_timestamp_output=TIMESTAMP
        )

        assert attribute.latest_timestamp_output == TIMESTAMP

    def test_output_entity_defaults(self) -> None:
        """The attribute, status and command lists default to empty lists."""
        entity = OutputDataEntityModel(id="output")

        assert not entity.attributes
        assert not entity.attributes_status
        assert not entity.commands

    def test_output_entity_with_config_models(self) -> None:
        """The output entity accepts attribute and command configuration models."""
        attribute = AttributeModel(id="storage__level")
        command = CommandModel(id="start")
        status = OutputDataAttributeModel(id="storage__level_status")

        entity = OutputDataEntityModel(
            id="output",
            attributes=[attribute],
            attributes_status=[status],
            commands=[command],
        )

        attributes = entity.attributes
        attributes_status = entity.attributes_status
        commands = entity.commands
        assert attributes is not None and attributes_status is not None
        assert commands is not None

        assert attributes[0].id == "storage__level"
        assert attributes_status[0] == status
        assert commands[0].id_interface == "start"

    def test_output_data_model(self) -> None:
        """The output data model holds a list of output entities."""
        model = OutputDataModel(entities=[OutputDataEntityModel(id="output")])

        assert model.entities[0].id == "output"


class TestComponentModel:
    """Tests for the component model."""

    def test_component_model_fields(self) -> None:
        """The component model stores entity and attribute ids."""
        component = ComponentModel(entity_id="entity", attribute_id="attribute")

        assert component.entity_id == "entity"
        assert component.attribute_id == "attribute"

    def test_component_model_requires_fields(self) -> None:
        """Missing fields raise a ValidationError."""
        with pytest.raises(ValidationError):
            ComponentModel(entity_id="entity")  # type: ignore[call-arg]


class TestValueConversion:
    """Tests for the value validators of the data transfer models."""

    def test_scalar_value_is_kept(self) -> None:
        """A scalar value is stored unchanged."""
        component = DataTransferComponentModel(
            entity_id="entity", attribute_id="attribute", value=42.5
        )

        assert component.value == 42.5
        assert component.unit is None
        assert component.timestamp is None

    def test_base_model_value_is_converted_to_dict(self) -> None:
        """A pydantic BaseModel value is converted to a json dictionary."""
        component = DataTransferComponentModel(
            entity_id="entity",
            attribute_id="attribute",
            value=ComponentModel(entity_id="inner", attribute_id="inner_attr"),
        )

        assert isinstance(component.value, dict)
        assert component.value == {
            "entity_id": "inner",
            "attribute_id": "inner_attr",
        }

    def test_series_value_is_converted_to_dataframe(self) -> None:
        """A pandas Series value is converted to a DataFrame."""
        series = pd.Series([1.0, 2.0], name="temperature")
        component = DataTransferComponentModel(
            entity_id="entity", attribute_id="attribute", value=series
        )

        assert isinstance(component.value, pd.DataFrame)
        pd.testing.assert_frame_equal(component.value, series.to_frame())

    def test_dataframe_value_is_kept(self) -> None:
        """A pandas DataFrame value is stored unchanged."""
        frame = pd.DataFrame({"temperature": [20.0]})
        component = DataTransferComponentModel(
            entity_id="entity", attribute_id="attribute", value=frame
        )

        assert isinstance(component.value, pd.DataFrame)
        pd.testing.assert_frame_equal(component.value, frame)

    def test_data_transfer_model_defaults(self) -> None:
        """The components list defaults to an empty list."""
        model = DataTransferModel()

        assert not model.components

    def test_data_transfer_model_with_components(self) -> None:
        """The data transfer model holds a list of components."""
        model = DataTransferModel(
            components=[
                DataTransferComponentModel(
                    entity_id="entity", attribute_id="attribute", value=1
                )
            ]
        )

        assert model.components[0].value == 1

    def test_timestamp_can_be_set(self) -> None:
        """The timestamp of a data transfer component can be set."""
        component = DataTransferComponentModel(
            entity_id="entity",
            attribute_id="attribute",
            value=1,
            unit=DataUnits.WHR,
            timestamp=TIMESTAMP,
        )

        assert component.unit is DataUnits.WHR
        assert component.timestamp == TIMESTAMP


class TestFiwareAndDatabaseModels:
    """Tests for the FIWARE and database parameter models."""

    def test_metadata_model_defaults(self) -> None:
        """Timestamp and unit default to None."""
        metadata = MetaDataModel()

        assert metadata.timestamp is None
        assert metadata.unit is None

    def test_fiware_auth_defaults(self) -> None:
        """All FiwareAuth fields are optional."""
        auth = FiwareAuth()

        assert auth.client_id is None
        assert auth.client_secret is None
        assert auth.token_url is None
        assert auth.bearer_token is None

    def test_fiware_auth_with_values(self) -> None:
        """FiwareAuth stores all given values."""
        auth = FiwareAuth(
            client_id="client",
            client_secret="secret",
            token_url="https://auth.example.com",
            bearer_token="token",
        )

        assert auth.client_id == "client"
        assert auth.bearer_token == "token"

    def test_fiware_parameter_requires_fields(self) -> None:
        """Missing required FIWARE parameters raise a ValidationError."""
        with pytest.raises(ValidationError):
            FiwareParameter(  # type: ignore[call-arg]
                cb_url="http://localhost:1026", service="openiot"
            )

    def test_fiware_parameter_with_authentication(self) -> None:
        """The FIWARE parameter model holds optional authentication data."""
        parameter = FiwareParameter(
            cb_url="http://localhost:1026",
            service="openiot",
            service_path="/",
            authentication=FiwareAuth(bearer_token="token"),
        )

        assert parameter.authentication is not None
        assert parameter.authentication.bearer_token == "token"

    def test_fiware_parameter_without_authentication(self) -> None:
        """The authentication defaults to None."""
        parameter = FiwareParameter(
            cb_url="http://localhost:1026", service="openiot", service_path="/"
        )

        assert parameter.authentication is None

    def test_database_parameter_defaults(self) -> None:
        """User defaults to None, password to an empty string and ssl to True."""
        parameter = DatabaseParameter(crate_db_url="http://localhost:4200")

        assert parameter.crate_db_url == "http://localhost:4200"
        assert parameter.crate_db_user is None
        assert parameter.crate_db_pw == ""
        assert parameter.crate_db_ssl is True

    def test_database_parameter_with_values(self) -> None:
        """The database parameter model stores all given values."""
        parameter = DatabaseParameter(
            crate_db_url="http://localhost:4200",
            crate_db_user="crate",
            crate_db_pw="password",
            crate_db_ssl=False,
        )

        assert parameter.crate_db_user == "crate"
        assert parameter.crate_db_pw == "password"
        assert parameter.crate_db_ssl is False

    def test_fiware_connection_parameter(self) -> None:
        """The connection parameter combines FIWARE and database parameters."""
        parameter = FiwareConnectionParameter(
            fiware_params=FiwareParameter(
                cb_url="http://localhost:1026",
                service="openiot",
                service_path="/",
            ),
            database_params=DatabaseParameter(crate_db_url="http://localhost:4200"),
        )

        assert parameter.fiware_params.service == "openiot"
        assert parameter.database_params.crate_db_ssl is True

    def test_fiware_connection_parameter_requires_fields(self) -> None:
        """Missing sub models raise a ValidationError."""
        with pytest.raises(ValidationError):
            FiwareConnectionParameter(  # type: ignore[call-arg]
                database_params=DatabaseParameter(crate_db_url="url")
            )


class TestFiwareDatapointParameter:
    """Tests for the FIWARE datapoint parameter model."""

    def test_fiware_datapoint_parameter(self) -> None:
        """The model holds entity, attribute and metadata."""
        entity = ContextEntity(id="urn:thermal_storage:01", type="Storage")
        attribute = AttributeModel(id="temperature_1")
        metadata = [
            NamedMetadata(
                name="timestamp", type="DateTime", value="2026-10-06T12:00:00Z"
            )
        ]

        parameter = FiwareDatapointParameter(
            entity=entity, attribute=attribute, metadata=metadata
        )

        assert parameter.entity.id == "urn:thermal_storage:01"
        assert parameter.attribute.id == "temperature_1"
        assert parameter.metadata[0].name == "timestamp"

    def test_fiware_datapoint_parameter_requires_metadata(self) -> None:
        """A missing metadata list raises a ValidationError."""
        with pytest.raises(ValidationError):
            FiwareDatapointParameter(  # type: ignore[call-arg]
                entity=ContextEntity(id="urn:thermal_storage:01", type="Storage"),
                attribute=AttributeModel(id="temperature_1"),
            )
