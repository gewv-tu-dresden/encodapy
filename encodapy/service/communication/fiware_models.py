"""
Description: This module contains the models for the Fiware service.
Author: Martin Altenburger
"""
from typing import Union, Optional
from pydantic import BaseModel
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import ContextEntity
from encodapy.config import AttributeModel

class FiwareDatapointParameter(BaseModel):
    """
    Model for the Fiware datapoint parameter.
    Contains:
        entity (ContextEntity): The entity of the datapoint
        attribute (AttributeModel): The attribute of the datapoint
        metadata (list[NamedMetadata]): The metadata of the attribute
    Args:
        BaseModel (BaseModel): Pydantic BaseModel of a datapoint in fiware
    """
    entity: ContextEntity
    attribute: AttributeModel
    metadata: list[NamedMetadata]

class FiwareAuth(BaseModel):
    """
    Base model for the Fiware authentication.
    Contains:
        client_id (str): The client id
        client_secret (str): The client secret
        token_url (str): The token url
        baerer_token (str): The baerer token
    """
    client_id:Optional[str]=None
    client_secret:Optional[str]=None
    token_url:Optional[str]=None
    baerer_token:Optional[str]=None

class FiwareParameter(BaseModel):
    """
    Model for the Fiware connection parameters.
    Contains:
        cb_url (str): The context broker url
        service (str): The service
        service_path (str): The service path
        authentication (Optional[Union[FiwareAuth, None]]): The authentication
    """
    cb_url:str
    service:str
    service_path:str
    authentication: Optional[Union[FiwareAuth, None]] = None

class DatabaseParameter(BaseModel):
    """
    Model for the database connection parameters.
    Contains:
        crate_db_url (str): The CrateDB url
        crate_db_user (Optional[str]): The CrateDB user
        crate_db_pw (Optional[str]): The CrateDB password
        crate_db_ssl (Optional[bool]): The CrateDB ssl
    """
    crate_db_url:str
    crate_db_user:Optional[Union[str, None]]=None
    crate_db_pw:Optional[str]=""
    crate_db_ssl:Optional[bool]=True

class FiwareConnectionParameter(BaseModel):
    """
    Model for the Fiware connection parameters.
    Contains:
        fiware_params (FiwareParameter): The Fiware parameters
        database_params (DatabaseParameter): The database parameters
    """
    fiware_params:FiwareParameter
    database_params:DatabaseParameter
