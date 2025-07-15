"""
Description: This file contains the class FiwareConnections, 
which is used to store the connection parameters for the Fiware and CrateDB connections.
Author: Martin Altenburger
"""

from asyncio import sleep
import os
from datetime import datetime, timedelta, timezone
from typing import Union, Optional
import concurrent.futures
import multiprocessing
from loguru import logger
import numpy as np
import pandas as pd
import requests
from dateutil import tz
from pydantic import BaseModel
from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import DataType, FiwareHeaderSecure
from filip.models.ngsi_v2.base import NamedMetadata
from filip.models.ngsi_v2.context import (
    ContextAttribute,
    ContextEntity,
    NamedCommand,
    NamedContextAttribute,
)

from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    CommandModel,
    DataQueryTypes,
    DefaultEnvVariables,
    InputModel,
    OutputModel,
    TimerangeTypes,
    ConfigModel
)
from encodapy.utils.error_handling import NoCredentials, InterfaceNotActive
from encodapy.utils.cratedb import CrateDBConnection
from encodapy.utils.fiware_auth import BaererToken
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    MetaDataModel,
    OutputDataAttributeModel,
    OutputDataEntityModel,
)
from encodapy.utils.units import (
    DataUnits,
    get_time_unit_seconds,
    get_unit_adjustment_factor,
)

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

class FiwareConnection:
    """
    Class for the connection to the Fiware plattform.
    Only a helper class.
    """

    def __init__(self):

        self.fiware_conn_params: FiwareConnectionParameter = None
        self.fiware_token_client: BaererToken = None
        self.fiware_header: FiwareHeaderSecure = None
        self.cb_client: ContextBrokerClient = None
        self.crate_db_client: CrateDBConnection = None
        self.config: ConfigModel

    def load_fiware_params(self):
        """
        Load the Fiware connection parameters.
        """

        if os.getenv(
            "FIWARE_AUTH", str(DefaultEnvVariables.FIWARE_AUTH.value)
        ).lower() in ("true", "1", "t"):

            if (
                os.environ.get("FIWARE_CLIENT_ID") is not None
                and os.environ.get("FIWARE_CLIENT_PW") is not None
                and os.environ.get("FIWARE_TOKEN_URL") is not None
            ):
                fiware_auth = FiwareAuth(
                    client_id=os.environ.get("FIWARE_CLIENT_ID"),
                    client_secret=os.environ.get("FIWARE_CLIENT_PW"),
                    token_url=os.environ.get("FIWARE_TOKEN_URL"))
            elif os.environ.get("FIWARE_BAERER_TOKEN") is not None:
                fiware_auth = FiwareAuth(
                    baerer_token= os.environ.get("FIWARE_BAERER_TOKEN"))
            else:
                logger.error("No authentication credentials available")
                raise NoCredentials
        else:
            fiware_auth = None

        fiware_params = FiwareParameter(
            cb_url=os.environ.get("CB_URL",
                                  DefaultEnvVariables.CB_URL.value),
            service=os.environ.get("FIWARE_SERVICE",
                                   DefaultEnvVariables.FIWARE_SERVICE.value),
            service_path=os.environ.get("FIWARE_SERVICE_PATH",
                                        DefaultEnvVariables.FIWARE_SERVICE_PATH.value),
            authentication=fiware_auth)

        database_params = DatabaseParameter(
            crate_db_url=os.environ.get("CRATE_DB_URL",
                                        DefaultEnvVariables.CRATE_DB_URL.value),
            crate_db_user=os.environ.get("CRATE_DB_USER",
                                         DefaultEnvVariables.CRATE_DB_USER.value),
            crate_db_pw=os.environ.get("CRATE_DB_PW",
                                        DefaultEnvVariables.CRATE_DB_PW.value),
            crate_db_ssl=os.environ.get("CRATE_DB_SSL",
                                        str(DefaultEnvVariables.CRATE_DB_SSL.value)).lower()
            in ("true", "1", "t"))

        self.fiware_conn_params = FiwareConnectionParameter(
            fiware_params=fiware_params,
            database_params=database_params
        )

    def prepare_fiware_connection(self):
        """
        Prepare the Fiware connection.
        """
        fiware_auth = self.fiware_conn_params.fiware_params.authentication

        if fiware_auth is not None:

            if fiware_auth.baerer_token is not None:
                self.fiware_token_client = BaererToken(
                    token=fiware_auth.baerer_token
                )
            else:
                self.fiware_token_client = BaererToken(
                    client_id=fiware_auth.client_id,
                    client_secret=fiware_auth.client_secret,
                    token_url=fiware_auth.token_url,
                )
            self.fiware_header = FiwareHeaderSecure(
                service=self.fiware_conn_params.fiware_params.service,
                service_path=self.fiware_conn_params.fiware_params.service_path,
                authorization=self.fiware_token_client.baerer_token,
            )
        else:
            self.fiware_header = FiwareHeaderSecure(
                service=self.fiware_conn_params.fiware_params.service,
                service_path=self.fiware_conn_params.fiware_params.service_path,
            )

        self.cb_client = ContextBrokerClient(
            url=self.fiware_conn_params.fiware_params.cb_url,
            fiware_header=self.fiware_header
        )

        self.crate_db_client = CrateDBConnection(
            crate_db_url=self.fiware_conn_params.database_params.crate_db_url,
            crate_db_user=self.fiware_conn_params.database_params.crate_db_user,
            crate_db_pw=self.fiware_conn_params.database_params.crate_db_pw,
            crate_db_ssl=self.fiware_conn_params.database_params.crate_db_ssl,
        )

    def update_authentication(self):
        """
        Update the authentication.
        """
        if self.fiware_conn_params.fiware_params.authentication is not None and (
            self.fiware_token_client.check_token() is False
            ):
            self.fiware_header.__dict__["authorization"] = (
                self.fiware_token_client.baerer_token
            )

    def _get_last_timestamp_for_fiware_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from the FIWARE platform

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]:
                - OutputDataEntityModel with timestamps for the attributes
                - the latest timestamp of the output entity for the attribute
                with the oldest value (None if no timestamp is available)
        """

        output_attributes_entity = self.cb_client.get_entity_attributes(
            entity_id=output_entity.id_interface
        )

        output_attributes_controller = {
            item.id_interface: item.id for item in output_entity.attributes
        }

        timestamps = []
        for attr in list(output_attributes_entity.keys()):
            if attr not in list(output_attributes_controller.keys()):
                continue
            if (output_attributes_entity[attr].metadata.get("TimeInstant") is not None
                and output_attributes_entity[attr].metadata.get("TimeInstant").value is not None):
                timestamps.append(
                    OutputDataAttributeModel(
                        id=output_attributes_controller[attr],
                        latest_timestamp_output=datetime.strptime(
                            output_attributes_entity[attr]
                            .metadata.get("TimeInstant")
                            .value,
                            "%Y-%m-%dT%H:%M:%S.%f%z",
                        ),
                    )
                )

        if len(timestamps) > 0:
            timestamp_latest_output = min(
                item.latest_timestamp_output for item in timestamps
            )
        else:
            timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_entity.id, attributes_status=timestamps),
            timestamp_latest_output,
        )

    def _get_metadata_from_fiware(
        self, fiware_attribute: ContextAttribute
    ) -> MetaDataModel:
        """Function to get the metadata from the fiware attribute

        Args:
            fiware_attribute (ContextAttribute): Fiware attribute

        Returns:
            MetaDataModel: Model with the metadata (timestamp, unit) of the attribute if available
        """
        metadata_lowercase = {
            k.lower(): v for k, v in fiware_attribute.metadata.items()
        }

        metadata_model = MetaDataModel()

        if metadata_lowercase.get("timeinstant") is not None:
            metadata_model.timestamp = datetime.strptime(
                metadata_lowercase.get("timeinstant").value, "%Y-%m-%dT%H:%M:%S.%f%z"
            )

        try:
            if metadata_lowercase.get("unitcode") is not None:
                metadata_model.unit = DataUnits(
                    metadata_lowercase.get("unitcode").value
                )
            elif metadata_lowercase.get("unittext") is not None:
                metadata_model.unit = DataUnits(
                    metadata_lowercase.get("unittext").value
                )
            elif metadata_lowercase.get("unit") is not None:
                metadata_model.unit = DataUnits(metadata_lowercase.get("unit").value)
        except ValueError as err:
            logger.error(
                f"Unit code {metadata_lowercase.get('unitcode').value} not available: {err}"
            )

        return metadata_model

    def get_data_from_fiware(
        self,
        method: DataQueryTypes,
        entity: InputModel,
        timestamp_latest_output: Union[datetime, None],
    ) -> Union[InputDataEntityModel, None]:
        """
        Function fetches the data for evaluation which have not yet been evaluated.
            First get the last timestamp of the output entity. Then get the data from
            the entity since the last timestamp of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
            - timestamp_latest_output (datetime): Timestamp of the last output

        Returns:
            - InputDataEntityModel: Model with the input data or None
            if the connection to the platform is not available

        """

        attributes_timeseries = {}
        attributes_values = []

        if self.cb_client is None:
            raise InterfaceNotActive
        try:

            fiware_input_entity_type = self.cb_client.get_entity(
                entity_id=entity.id_interface
            ).type
            fiware_input_entity_attributes = self.cb_client.get_entity_attributes(
                entity_id=entity.id_interface, entity_type=fiware_input_entity_type
            )
        except requests.exceptions.ConnectionError as err:
            logger.error(f"""No connection to platform (ConnectionError): {err}""")

            return None

        for attribute in entity.attributes:

            if attribute.id_interface not in fiware_input_entity_attributes:
                logger.error(
                    f"Attribute {attribute.id_interface} not found in entity {entity.id_interface}"
                )
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=None,
                        data_type=attribute.type,
                        data_available=False,
                        latest_timestamp_input=None,
                        unit=None,
                    )
                )

                continue

            if attribute.type == AttributeTypes.TIMESERIES:
                attributes_timeseries[attribute.id] = {
                    "id_interface": attribute.id_interface,
                    "metadata": self._get_metadata_from_fiware(
                        fiware_input_entity_attributes[attribute.id_interface]
                    ),
                }

            elif attribute.type == AttributeTypes.VALUE:

                metadata = self._get_metadata_from_fiware(
                    fiware_input_entity_attributes[attribute.id_interface]
                )
                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=fiware_input_entity_attributes[
                            attribute.id_interface
                        ].value,
                        data_type=AttributeTypes.VALUE,
                        data_available=(
                            fiware_input_entity_attributes[attribute.id_interface].value
                            is not None
                        ),
                        latest_timestamp_input=metadata.timestamp,
                        unit=metadata.unit,
                    )
                )
            else:
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )
                raise NotImplementedError

        if len(attributes_timeseries) > 0:

            attributes_values.extend(
                self.get_data_from_datebase(
                    entity=ContextEntity(id=entity.id_interface,
                                         type=fiware_input_entity_type),
                    entity_attributes=attributes_timeseries,
                    method=method,
                    timestamp_latest_output=timestamp_latest_output,
                )
            )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def _calculate_timerange(
        self,
        time_now: datetime,
        last_timestamp: Union[datetime, None],
        timerange_value: int,
        timerange_type: Union[TimerangeTypes, None],
    ) -> tuple[str, str]:
        """Function to calculate the timerange for the input data query based on
        a fixed timerange from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output
            timerange_value (int): Value of the timerange in the configuration
            timerange_type (str): Type of the timerange (absolute or relative)

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        if timerange_type is TimerangeTypes.ABSOLUTE or last_timestamp is None:
            from_date = (
                time_now - timedelta(seconds=timerange_value)
            ).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None

        timeframe = (time_now - last_timestamp).total_seconds() / 60

        if timerange_type is TimerangeTypes.RELATIVE:
            if timeframe < timerange_value:
                from_date = (
                    time_now
                    - timedelta(seconds=timerange_value)
                ).strftime("%Y-%m-%dT%H:%M:%S%z")
                return from_date, None

            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            to_date = (
                last_timestamp
                + timedelta(seconds=timerange_value)
            ).strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, to_date

        # Fallback to absolute if no type is specified
        from_date = (
            time_now - timedelta(seconds=timerange_value)
        ).strftime("%Y-%m-%dT%H:%M:%S%z")
        return from_date, None

    def _calculate_timerange_min_max(
        self,
        time_now: datetime,
        last_timestamp: Union[datetime, None],
        timerange_min: int,
        timerange_max: int,
    ) -> tuple[str, str]:
        """Function to calculate the timerange for the input data query based on a min
        and max timerange from the configuration

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output, if available
            timerange_min (int): Minimal value of the timerange in the configuration in seconds
            timerange_max (int): Maximal value of the timerange in the configuration in seconds
            timerange_type (TimerangeTypes): Type of the timerange (absolute or relative)

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        if last_timestamp is None:
            from_date = (
                (time_now - timedelta(seconds=timerange_max))
                .replace(tzinfo=tz.UTC)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            return from_date, None

        timeframe = (time_now - last_timestamp).total_seconds() / 60

        if timeframe < timerange_min:
            from_date = (
                (time_now - timedelta(seconds=timerange_min))
                .replace(tzinfo=tz.UTC)
                .strftime("%Y-%m-%dT%H:%M:%S%z")
            )
            return from_date, None

        if timeframe < timerange_max:
            from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
            return from_date, None

        from_date = last_timestamp.strftime("%Y-%m-%dT%H:%M:%S%z")
        to_date = (
            last_timestamp + timedelta(seconds=timerange_max )
        ).strftime("%Y-%m-%dT%H:%M:%S%z")
        return from_date, to_date

    def _handle_calculation_method(
        self,
        time_now: datetime,
        last_timestamp: datetime,
    ) -> tuple[str, str]:
        """Funtion to calculate the dates for the calculation method

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calculation = self.config.controller_settings.time_settings.calculation

        if calculation.timerange is not None:
            return self._calculate_timerange(
                time_now,
                last_timestamp,
                calculation.timerange * get_time_unit_seconds(calculation.timerange_unit),
                calculation.timerange_type,
            )
        if (
            calculation.timerange_min is not None
            and calculation.timerange_max is not None
        ):
            if calculation.timerange_type is TimerangeTypes.ABSOLUTE:
                return self._calculate_timerange(
                    time_now,
                    last_timestamp,
                    calculation.timerange_max * get_time_unit_seconds(calculation.timerange_unit),
                    calculation.timerange_type,
                )

            return self._calculate_timerange_min_max(
                time_now,
                last_timestamp,
                calculation.timerange_min * get_time_unit_seconds(calculation.timerange_unit),
                calculation.timerange_max * get_time_unit_seconds(calculation.timerange_unit),
            )

        logger.error(
            "No Information about the input time ranges for the calculation in the configuration."
        )
        return None, None

    def _calculate_dates(
        self,
        method: DataQueryTypes,
        last_timestamp: Union[datetime, None]
    ) -> tuple[str, str]:
        """Function to calculate the dates for the input data query

        Args:
            method (DataQueryTypes): Method for the calculation
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """

        time_now = datetime.now(timezone.utc)

        from_date, to_date = None, None

        if method is DataQueryTypes.CALCULATION:
            from_date, to_date = self._handle_calculation_method(
                time_now, last_timestamp
            )
        elif method is DataQueryTypes.CALIBRATION:
            from_date, to_date = self._handle_calibration_method(
                time_now, last_timestamp
            )

        if to_date is None:
            to_date = time_now.strftime("%Y-%m-%dT%H:%M:%S%z")

        return from_date, to_date

    def _handle_calibration_method(
        self,
        time_now: datetime,
        last_timestamp: Union[datetime, None]
    ) -> tuple[str, str]:
        """Funtion to calculate the dates for the calibration method
            - Use the last timestamp of the output entity as the from_date if available
            and time range is relative
            - Use the timenow - timerange as the from_date if the time range is absolute
            or no last timestamp is available

        Args:
            time_now (datetime): Time now
            last_timestamp (datetime): Timestamp of the last output, if available

        Returns:
            tuple[str, str]: Timestamps for the input data query (from_date, to_date)
        """
        calibration_time_settings = (
            self.config.controller_settings.time_settings.calibration
        )

        timerange = calibration_time_settings.timerange * get_time_unit_seconds(
            calibration_time_settings.timerange_unit
        )

        if (
            self.config.controller_settings.time_settings.calculation.timerange_type
            is TimerangeTypes.RELATIVE
            and last_timestamp is not None
        ):
            from_date = (last_timestamp - timedelta(seconds=timerange)).strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            )
            to_date = last_timestamp

            return from_date, None

        from_date = (time_now - timedelta(seconds=timerange)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        to_date = time_now

        return from_date, to_date

    def get_data_from_datebase(
        self,
        entity: ContextEntity,
        entity_attributes: dict,
        method: DataQueryTypes,
        timestamp_latest_output: datetime,
    ) -> list[InputDataAttributeModel]:
        """
        Function to get the data from the database for the input attributes (crateDB is used)

        Args:
            - entity_id: id of the entity
            - entity_type: type of the entity
            - entity_attributes: dict with the attributes of the entity (id, metadata)
            - method (DataQueryTypes): method of the function which queries the data
            (calculation or calibration)
            - timestamp_latest_output: timestamp of the last output of the entity

        Returns:
            - list of InputDataAttributeModel: list with the input attributes

        TODO:
            - Does it make sense to use the quantumleap client for this?
                https://github.com/RWTH-EBC/FiLiP/blob/master/filip/clients/ngsi_v2/quantumleap.py#L449
            - Improve the error handling
        """

        from_date, to_date = self._calculate_dates(
            method=method, last_timestamp=timestamp_latest_output
        )

        df = self.crate_db_client.get_data(
            service=self.fiware_conn_params.fiware_params.service,
            entity=entity,
            attributes=[
                attribute["id_interface"] for attribute in entity_attributes.values()
            ],
            from_date=from_date,
            to_date=to_date,
            limit=1000000,
        )

        if df.empty:
            logger.debug("Service has not received data from CrateDB")
            return []

        # resample the time series with configured time step size
        df.fillna(value=np.nan, inplace=True)
        time_step_seconds = int(
            self.config.controller_settings.time_settings.calculation.timestep
            * get_time_unit_seconds(
                self.config.controller_settings.time_settings.calculation.timestep_unit
            )
        )
        df = df.resample(f"""{time_step_seconds}s""").mean(numeric_only=True)

        input_attributes = []

        for attribute_id, attribute_data in entity_attributes.items():
            df.rename(
                columns={attribute_data["id_interface"]: attribute_id}, inplace=True
            )
            data = df.filter([attribute_id]).dropna()
            if data.empty:
                logger.debug(
                    f"Data for attribute {attribute_id} of entity {entity.id} is empty"
                )
                input_attributes.append(
                    InputDataAttributeModel(
                        id=attribute_id,
                        data=None,
                        data_type=AttributeTypes.TIMESERIES,
                        data_available=False,
                        latest_timestamp_input=None,
                        unit=attribute_data["metadata"].unit,
                    )
                )
            else:
                logger.debug(
                    f"Service received data from CrateDB for attribute {attribute_id} "
                    f"of entity {entity.id}"
                )
                input_attributes.append(
                    InputDataAttributeModel(
                        id=attribute_id,
                        data=data,
                        data_type=AttributeTypes.TIMESERIES,
                        data_available=True,
                        latest_timestamp_input=to_date,
                        unit=attribute_data["metadata"].unit,
                    )
                )

        return input_attributes

    def update_fiware_entity(
        self,
        entity_id: str,
        entity_type: str,
        attrs: list[NamedContextAttribute],
    ) -> None:
        """
        Function to update the entity in the FIWARE platform with filip

        Args:
            entity_id (str): ID of the entity
            entity_type (str): Type of the entity
            attrs (list[NamedContextAttribute]): List with the attributes to update
        """

        self.cb_client.update_or_append_entity_attributes(
            entity_id=entity_id, entity_type=entity_type, attrs=attrs
        )

    async def _send_timeseries_to_fiware(
        self,
        entity_id: str,
        entity_type: str,
        attrs_timeseries: list[NamedContextAttribute],
    ) -> None:
        """
        Function to send the timeseries data to the FIWARE platform in async mode
        and parallel processing

        Args:
            entity_id (str): ID of the entity
            entity_type (str): Type of the entity
            attrs_timeseries (list[NamedContextAttribute]): List with the timeseries data
        TODO:
            - Is there a better way to send the data from dataframes to the FIWARE platform?
        """
        max_workers = multiprocessing.cpu_count()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for attribute in attrs_timeseries:
                future = executor.submit(
                    self.update_fiware_entity, entity_id, entity_type, [attribute]
                )
                futures.append(future)

                await sleep(0.01)

            concurrent.futures.wait(futures)

    async def prepare_timeseries_for_fiware(
        self,
        fiware_datapoint: FiwareDatapointParameter,
        datatype: DataType,
        factor_unit_adjustment: float,
    ) -> list[NamedContextAttribute]:
        """
        Function to prepare the timeseries data for the FIWARE platform

        Args:
            fiware_datapoint (FiwareDatapointParameter): Fiware datapoint parameter
            datatype (DataType): Datatype of the attribute
            factor_unit_adjustment (float): Factor to adjust the unit

        Returns:
            list: List with the attributes (NamedContextAttribute) for the FIWARE platform
        """
        if len(fiware_datapoint.attribute.value) == 0:
            return
        if fiware_datapoint.attribute.id not in fiware_datapoint.attribute.value.columns:
            logger.error(f"Attribute {fiware_datapoint.attribute.id} not in the dataframe.")
            return
        df = fiware_datapoint.attribute.value.sort_index()
        attrs_timeseries = []

        meta_data_row = fiware_datapoint.metadata + [
            NamedMetadata(
                name="TimeInstant",
                type=DataType.DATETIME,
                value=df.index[-1].strftime("%Y-%m-%dT%H:%M:%S%z"),
            )
        ]

        attr = NamedContextAttribute(
            name=fiware_datapoint.attribute.id_interface,
            value=df[fiware_datapoint.attribute.id].iloc[-1] * factor_unit_adjustment,
            type=datatype,
            metadata=meta_data_row,
        )

        for index, row in fiware_datapoint.attribute.value.iterrows():
            if index == df.index[-1]:
                continue

            meta_data_row = fiware_datapoint.metadata + [
                NamedMetadata(
                    name="TimeInstant",
                    type=DataType.DATETIME,
                    value=index.strftime("%Y-%m-%dT%H:%M:%S%z"),
                )
            ]

            attrs_timeseries.append(
                NamedContextAttribute(
                    name=fiware_datapoint.attribute.id_interface,
                    value=row[fiware_datapoint.attribute.id] * factor_unit_adjustment,
                    type=datatype,
                    metadata=meta_data_row,
                )
            )
        if len(attrs_timeseries) > 0:
            await self._send_timeseries_to_fiware(
                entity_id=fiware_datapoint.entity.id,
                entity_type=fiware_datapoint.entity.type,
                attrs_timeseries=attrs_timeseries,
            )

        return attr

    async def _send_data_to_fiware(
        self,
        output_entity: OutputModel,
        output_attributes: list[AttributeModel],
        output_commands: list[CommandModel],
    ) -> None:
        """
        Function to send the output data to the FIWARE platform

        Args:
            - output_entity: OutputModel with the output entity
            - output_attributes: list with the output attributes
            - output_commands: list with the output commands

        TODO:
            - Is there a better way to send the data from dataframes to the FIWARE platform?
        """

        fiware_entity = self.cb_client.get_entity(output_entity.id_interface)

        entity_attributes = self.cb_client.get_entity_attributes(
            entity_id=fiware_entity.id, entity_type=fiware_entity.type
        )

        attrs = []
        for attribute in output_attributes:

            fiware_unit = None
            factor_unit_adjustment = 1

            if attribute.id_interface in entity_attributes:
                datatype = entity_attributes[attribute.id_interface].type
                if (
                    entity_attributes[attribute.id_interface].metadata.get("unitCode")
                    is not None
                ):
                    fiware_unit = DataUnits(
                        entity_attributes[attribute.id_interface]
                        .metadata.get("unitCode")
                        .value
                    )
            else:
                datatype = attribute.datatype

            meta_data = []

            if attribute.unit is not None and fiware_unit is None:
                meta_data.append(
                    NamedMetadata(
                        name="unitCode", type=DataType.TEXT, value=attribute.unit.value
                    )
                )
            elif attribute.unit is None:
                logger.debug(
                    f"No information about the unit of the attribute {attribute.id} "
                    f"from entity {output_entity.id} available!"
                )

            elif fiware_unit is not attribute.unit:

                factor_unit_adjustment = get_unit_adjustment_factor(
                    unit_actual=attribute.unit, unit_target=fiware_unit
                )

            if isinstance(attribute.value, pd.DataFrame):

                attrs.append(
                    await self.prepare_timeseries_for_fiware(
                        fiware_datapoint = FiwareDatapointParameter(
                            entity=ContextEntity(id= fiware_entity.id,
                                                 type= fiware_entity.type),
                            attribute=attribute,
                            metadata=meta_data),
                        datatype=datatype,
                        factor_unit_adjustment=factor_unit_adjustment,
                    )
                )
                continue

            meta_data.append(
                NamedMetadata(
                    name="TimeInstant",
                    type=DataType.DATETIME,
                    value=attribute.timestamp.strftime("%Y-%m-%dT%H:%M:%S%z"),
                )
            )

            attrs.append(
                NamedContextAttribute(
                    name=attribute.id_interface,
                    value=(
                        attribute.value * factor_unit_adjustment
                        if attribute.value is not None
                        else None
                    ),
                    type=datatype,
                    metadata=meta_data,
                )
            )

        cmds = []
        for command in output_commands:
            cmds.append(
                NamedCommand(
                    name=command.id_interface,
                    value=command.value,
                    type=DataType.COMMAND,
                )
            )

        output_points = attrs + cmds

        if len(output_points) == 0:
            logger.debug("No output data available for sending to the FIWARE platform.")
            return

        if len(attrs)>0:
            i = 0
            while i < 3:
                try:
                    self.cb_client.update_or_append_entity_attributes(
                        entity_id=fiware_entity.id,
                        entity_type=fiware_entity.type,
                        attrs=attrs,
                    )
                    break
                except requests.exceptions.HTTPError as err:
                    if i < 3:
                        await sleep(0.1)
                    else:
                        logger.error(
                            f"HTTPError while sending attributes to FIWARE platform: {err}"
                        )

                i += 1

        if len(cmds)>0:
            i = 0
            while i < 3:
                try:
                    self.cb_client.update_existing_entity_attributes(
                        entity_id=fiware_entity.id,
                        entity_type=fiware_entity.type,
                        attrs= cmds,
                    )
                    break
                except requests.exceptions.HTTPError as err:
                    if i < 3:
                        await sleep(0.1)
                    else:
                        logger.error(
                            f"HTTPError while sending commands to FIWARE platform: {err}"
                        )

                i += 1
