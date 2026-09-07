"""
Description: Class to connect to a CrateDB and query data from it
Author: Martin Altenburger
"""
from typing import Optional
import crate.client # type: ignore[import-untyped]
import pandas as pd
from filip.models.ngsi_v2.context import ContextEntity
from loguru import logger

class CrateDBConnection:
    """
    Class for a connection to a CrateDB

    Args:
        - crate_db_url: URL of the CrateDB
        - crate_db_user: Name of the User of CrateDB
        - crate_db_pw: Password of the User of CrateDB
        - crate_db_ssl: Verify the SSL-Cert?
    """

    def __init__(
        self,
        crate_db_url: str,
        crate_db_user: Optional[str] = None,
        crate_db_pw: Optional[str] = None,
        crate_db_ssl: bool = False,
    ) -> None:
        self.crate_db_url = crate_db_url
        self.crate_db_user = crate_db_user
        self.crate_db_pw = crate_db_pw
        self.crate_db_ssl = crate_db_ssl

    def get_database_connection(self) -> crate.client.connection:
        """
        Function to get a connection to the CrateDB
        Return:
            connection: Connection to the CrateDB
        """
        if self.crate_db_user is None:
            connection = crate.client.connect(self.crate_db_url)
        else:
            connection = crate.client.connect(
                self.crate_db_url,
                username=self.crate_db_user,
                password=self.crate_db_pw,
                verify_ssl_cert=self.crate_db_ssl,
            )

        return connection

    def query_existing_attributes(
        self,
        service: str,
        entity_type: str,
        attributes: list,
    ) -> list:
        """
        Function to query existing attributes of an entity type
        Args:
            service (str): Name of the Fiware Service
            entity_type (str): type of the entity
            attributes (list): list of attribute names
        Return:
            list: list of existing attributes
        """
        connection = self.get_database_connection()

        cursor = connection.cursor()

        attrs = "'time_index'"
        for attribute in list(attributes):
            attrs += ", '" + str(attribute) + "'"

        # check which column exists
        cursor.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = 'et{entity_type.lower()}' "
            f"AND table_schema = 'mt{service}' "
            f"AND column_name IN ({attrs})"
        )
        attributes_db = list({column[0] for column in cursor.fetchall()})

        cursor.close()
        connection.close()

        return attributes_db

    def get_data(
        self,
        service: str,
        entity: ContextEntity,
        attributes: list,
        from_date: str,
        to_date: str,
        limit: int = 100000,
    ):
        """
        Function to query data from cratedb

        Args:
            - service: Name of the Fiware Service
            - entity (ContextEntity): Fiware Entity
            - attributes: list of attribute names
            - from_date: timestamp from which data is to be retrieved\
                (Milliseconds or Datetime (%Y-%m-%dT%H:%M:%S%z))
            - to_date: timestamp up to which data is to be retrieved\
                (Milliseconds or Datetime (%Y-%m-%dT%H:%M:%S%z))
            - limit: maximal number of datapoints

        Return:
            - dataframe with time index in utc and attributes as columns
        """
        attributes_db = self.query_existing_attributes(
            service=service, entity_type=entity.type, attributes=attributes
        )

        if len(attributes_db) == 0:
            logger.warning(
                f"No attributes found in CrateDB for entity {entity.id} of type {entity.type} "
                f"in service {service}."
                )
            return pd.DataFrame()

        connection = self.get_database_connection()
        cursor = connection.cursor()

        # query existing columns
        attrs = ""
        attrs_not_null = ""
        for attribute in attributes_db:
            if attribute == attributes_db[-1]:
                attrs += '"' + str(attribute) + '"'

            else:
                attrs += '"' + str(attribute) + '", '

            if attribute != "time_index" and attrs_not_null != "":
                attrs_not_null += ' OR "' + str(attribute) + '" IS NOT NULL'
            elif attribute != "time_index":
                attrs_not_null += '"' + str(attribute) + '" IS NOT NULL'

        cursor.execute(
            f"SELECT {attrs} FROM mt{service}.et{entity.type} "
            f"WHERE entity_id = '{entity.id}' "
            f"AND time_index > '{from_date}' AND time_index < '{to_date}' "
            f"AND ({attrs_not_null}) "
            f"limit {limit}"
        )
        results = cursor.fetchall()

        if len(results) > 0:
            df = pd.DataFrame(results)

            df.columns = pd.Index([desc[0] for desc in cursor.description])

            df['time_index'] = pd.to_datetime(df.time_index, unit="ms").dt.tz_localize(
                "UTC"
            )
            df.rename(columns={"time_index": "datetime"}, inplace=True)
            df.set_index(keys="datetime", drop=True, inplace=True)

        else:
            df = pd.DataFrame()

        cursor.close()
        connection.close()

        return df
