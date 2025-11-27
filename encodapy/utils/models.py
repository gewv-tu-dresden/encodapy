"""
Description: This file contains the models for the use in the system controller itself.
Authors: Martin Altenburger
"""

from datetime import datetime
from typing import Dict, List, Optional, Union
from pandas import DataFrame
from pydantic import BaseModel, ConfigDict, field_validator
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import ContextEntity
from encodapy.config.models import AttributeModel, CommandModel
from encodapy.config.types import AttributeTypes
from encodapy.utils.units import DataUnits


class InputDataAttributeModel(BaseModel):
    """
    Model for a attribute of input data of the system controller.

    Attributes:
        id (str): The id of the input data attribute
        data (Union[str, float, int, bool, Dict, List, DataFrame, None]): \
            The input data as a DataFrame or a single value
        unit (Union[DataUnits, None]): The unit of the input data
        data_type (AttributeTypes): The type of the input data (AttributeTypes)
        data_available (bool): If the data is available
        latest_timestamp_input (Union[datetime, None]): \
            The latest timestamp of the input data from the query or None,\
            if the data is not available
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    data: Union[str, float, int, bool, Dict, List, DataFrame, None]
    unit: Union[DataUnits, None] = None
    data_type: AttributeTypes
    data_available: bool
    latest_timestamp_input: Union[datetime, None]


class InputDataEntityModel(BaseModel):
    """
    Model for the input data of the system controller.

    Attributes:
        id: The id of the input data entity
        attributes: List of the input data attributes as InputDataAttributeModel
    """

    id: str
    attributes: List[InputDataAttributeModel]


class StaticDataEntityModel(InputDataEntityModel):
    """
    Model for the static data of the system controller, same like InputDataEntityModel.

    Attributes:
        id: The id of the input data entity
        attributes: List of the input data attributes as InputDataAttributeModel
    """


class OutputDataAttributeModel(BaseModel):
    """
    Model for a attribute of output data of the system controller - status based on the status\
        of the interface.

    Attributes:
        id: The id of the output data attribute
        latest_timestamp_output: The latest timestamp of the output data from the query or None,\
            if the data is not available
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    latest_timestamp_output: Optional[Union[datetime, None]] = None


class OutputDataEntityModel(BaseModel):
    """
    Model for the status of the output data of the system controller.

    Attributes:
        id: The id of the output entity
        latest_timestamp_output: The latest timestamp of the output data from the query or None,\
            if the data is not available
        attributes: List of the output data attributes as OutputDataAttributeModel
        commands: List of the output data commands as OutputDataCommandModel

    """

    id: str
    attributes: Optional[List[AttributeModel]] = []
    attributes_status: Optional[List[OutputDataAttributeModel]] = []
    commands: Optional[List[CommandModel]] = []


class InputDataModel(BaseModel):
    """
    Model for the input data of the system controller.

    Attributes:
        input_entities: List of the input data entities as InputDataEntityModel
        output_entities: List of the output data entities as OutputDataEntityModel
        static_entities: List of the static data entities as StaticDataEntityModel
    """

    input_entities: list[InputDataEntityModel]
    output_entities: list[OutputDataEntityModel]
    static_entities: list[StaticDataEntityModel]


class OutputDataModel(BaseModel):
    """
    Model for the output data of the system controller.

    Attributes:
        entities: List of the output data entitys as OutputDataEntityModel
    """

    entities: list[OutputDataEntityModel]


class ComponentModel(BaseModel):
    """
    Model for the dataflow (input/output) of the controller.

    Attributes:
        entity: The entity (input / output) of the datapoint for the controller
        attribute: The attribute of the datapoint for the controller
    """

    entity_id: str
    attribute_id: str


class DataTransferComponentModel(ComponentModel):
    """
    Model for the components of the data transfer between calculation and the basic service.

    Attributes:
        entity_id: The id of the entity of the component
        attribute_id: The id of the attribute of the component
        value: The output data value as OutputDataModel
        unit: The unit of the output data
        timestamp: The timestamp of the output
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Union[str, float, int, bool, Dict, List, DataFrame, None]
    unit: Union[DataUnits, None] = None
    timestamp: Optional[Union[datetime, None]] = None

    @field_validator('value', mode='before')
    @classmethod
    def convert_value_to_dict(cls, val):
        """
        Convert a Pydantic BaseModel value to a dictionary.
        """
        if isinstance(val, BaseModel):
            return val.model_dump(mode='json')
        return val


class DataTransferModel(BaseModel):
    """
    Model for the data transfer between calculation and the basic service.

    Attributes:
        components: List of the components of the data transfer as DataTransferComponentModel
    """

    components: list[DataTransferComponentModel] = []


# Models for the Fiware Connection
class MetaDataModel(BaseModel):
    """
    Model for the metadata of datapoints of the controller.

    Attributes:
        timestamp: The timestamp of the data
        unit: The unit of the data
    """

    timestamp: Union[datetime, None] = None
    unit: Union[DataUnits, None] = None


class FiwareDatapointParameter(BaseModel):
    """
    Model for the Fiware datapoint parameter.

    Attributes:
        entity (ContextEntity): The entity of the datapoint
        attribute (AttributeModel): The attribute of the datapoint
        metadata (list[NamedMetadata]): The metadata of the attribute
    """

    entity: ContextEntity
    attribute: AttributeModel
    metadata: list[NamedMetadata]


class FiwareAuth(BaseModel):
    """
    Base model for the Fiware authentication.

    Attributes:
        client_id (str): The client id
        client_secret (str): The client secret
        token_url (str): The token url
        baerer_token (str): The baerer token
    """

    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    baerer_token: Optional[str] = None


class FiwareParameter(BaseModel):
    """
    Model for the Fiware connection parameters.

    Attributes:
        cb_url (str): The context broker url
        service (str): The service
        service_path (str): The service path
        authentication (Optional[Union[FiwareAuth, None]]): The authentication
    """

    cb_url: str
    service: str
    service_path: str
    authentication: Optional[Union[FiwareAuth, None]] = None


class DatabaseParameter(BaseModel):
    """
    Model for the database connection parameters.

    Attributes:
        crate_db_url (str): The CrateDB url
        crate_db_user (Optional[str]): The CrateDB user
        crate_db_pw (Optional[str]): The CrateDB password
        crate_db_ssl (Optional[bool]): The CrateDB ssl
    """

    crate_db_url: str
    crate_db_user: Optional[Union[str, None]] = None
    crate_db_pw: Optional[str] = ""
    crate_db_ssl: Optional[bool] = True


class FiwareConnectionParameter(BaseModel):
    """
    Model for the Fiware connection parameters.

    Attributes:
        fiware_params (FiwareParameter): The Fiware parameters
        database_params (DatabaseParameter): The database parameters
    """

    fiware_params: FiwareParameter
    database_params: DatabaseParameter
