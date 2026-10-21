"""Unit tests for encodapy.utils.cratedb with mocked database connections."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from filip.models.ngsi_v2.context import ContextEntity

from encodapy.utils.cratedb import CrateDBConnection


@pytest.fixture(name="db_connection")
def fixture_db_connection() -> CrateDBConnection:
    """A CrateDBConnection with credentials for the mocked connection tests."""
    return CrateDBConnection(
        crate_db_url="http://localhost:4200",
        crate_db_user="cratedb",
        crate_db_pw="secret",
        crate_db_ssl=False,
    )


def _mock_cursor(fetchall_result: list, description: list | None = None) -> MagicMock:
    """Create a mock cursor with a defined fetchall result and description."""
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall_result
    if description is not None:
        cursor.description = description
    return cursor


def test_init_stores_connection_parameters() -> None:
    """The constructor stores all connection parameters."""

    connection = CrateDBConnection(
        crate_db_url="http://localhost:4200",
        crate_db_user="user",
        crate_db_pw="password",
        crate_db_ssl=True,
    )

    assert connection.crate_db_url == "http://localhost:4200"
    assert connection.crate_db_user == "user"
    assert connection.crate_db_pw == "password"
    assert connection.crate_db_ssl is True


def test_get_database_connection_without_user(db_connection: CrateDBConnection) -> None:
    """Without a user the connection is established without credentials."""

    db_connection.crate_db_user = None

    with patch("crate.client.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        connection = db_connection.get_database_connection()

    assert connection is mock_connect.return_value
    mock_connect.assert_called_once_with("http://localhost:4200")


def test_get_database_connection_with_user(db_connection: CrateDBConnection) -> None:
    """With a user the connection is established with credentials."""

    with patch("crate.client.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        connection = db_connection.get_database_connection()

    assert connection is mock_connect.return_value
    mock_connect.assert_called_once_with(
        "http://localhost:4200",
        username="cratedb",
        password="secret",
        verify_ssl_cert=False,
    )


def test_query_existing_attributes_returns_existing_columns(
    db_connection: CrateDBConnection,
) -> None:
    """Only attributes that exist as columns are returned."""

    cursor = _mock_cursor([("time_index",), ("temperature",)])
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with patch("crate.client.connect", return_value=connection):
        attributes = db_connection.query_existing_attributes(
            service="test_service",
            entity_type="WeatherObserved",
            attributes=["temperature", "pressure"],
        )

    assert set(attributes) == {"time_index", "temperature"}
    executed_sql = cursor.execute.call_args[0][0]
    assert "etweatherobserved" in executed_sql
    assert "mttest_service" in executed_sql
    assert "'temperature'" in executed_sql
    assert "'pressure'" in executed_sql
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_get_data_without_attributes_returns_empty_dataframe(
    db_connection: CrateDBConnection,
) -> None:
    """If no attributes exist in the database an empty DataFrame is returned."""

    entity = ContextEntity(id="test:id", type="WeatherObserved")

    with patch.object(
        CrateDBConnection, "query_existing_attributes", return_value=[]
    ) as mock_query:
        dataframe = db_connection.get_data(
            service="test_service",
            entity=entity,
            attributes=["temperature"],
            from_date="2026-01-01T00:00:00+00:00",
            to_date="2026-01-02T00:00:00+00:00",
        )

    assert dataframe.empty
    mock_query.assert_called_once_with(
        service="test_service",
        entity_type="WeatherObserved",
        attributes=["temperature"],
    )


def test_get_data_with_results_returns_utc_dataframe(
    db_connection: CrateDBConnection,
) -> None:
    """Results are returned as DataFrame with a UTC datetime index."""

    entity = ContextEntity(id="test:id", type="WeatherObserved")
    cursor = _mock_cursor(
        fetchall_result=[
            (20.5, 1013.0, 1767225600000),
            (21.5, 1012.0, 1767229200000),
        ],
        description=[("temperature",), ("pressure",), ("time_index",)],
    )
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with patch.object(
        CrateDBConnection,
        "query_existing_attributes",
        return_value=["temperature", "pressure", "time_index"],
    ):
        with patch("crate.client.connect", return_value=connection):
            dataframe = db_connection.get_data(
                service="test_service",
                entity=entity,
                attributes=["temperature", "pressure"],
                from_date="2026-01-01T00:00:00+00:00",
                to_date="2026-01-02T00:00:00+00:00",
            )

    assert isinstance(dataframe.index, pd.DatetimeIndex)
    assert dataframe.index.tz is not None
    assert str(dataframe.index.tz) == "UTC"
    assert list(dataframe["temperature"]) == [20.5, 21.5]
    assert list(dataframe["pressure"]) == [1013.0, 1012.0]
    executed_sql = cursor.execute.call_args[0][0]
    assert "entity_id = 'test:id'" in executed_sql
    assert '"temperature" IS NOT NULL OR "pressure" IS NOT NULL' in executed_sql
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


def test_get_data_without_results_returns_empty_dataframe(
    db_connection: CrateDBConnection,
) -> None:
    """An empty query result returns an empty DataFrame."""

    entity = ContextEntity(id="test:id", type="WeatherObserved")
    cursor = _mock_cursor(fetchall_result=[])
    connection = MagicMock()
    connection.cursor.return_value = cursor

    with patch.object(
        CrateDBConnection,
        "query_existing_attributes",
        return_value=["time_index", "temperature"],
    ):
        with patch("crate.client.connect", return_value=connection):
            dataframe = db_connection.get_data(
                service="test_service",
                entity=entity,
                attributes=["temperature"],
                from_date="2026-01-01T00:00:00+00:00",
                to_date="2026-01-02T00:00:00+00:00",
            )

    assert isinstance(dataframe, pd.DataFrame)
    assert dataframe.empty
