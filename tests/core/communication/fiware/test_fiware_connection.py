"""
Tests for FIWARE connection and configuration management in EnCoDaPy.

This module tests the FiwareConnection class functionality for:
- Loading FIWARE parameters from environment variables
- Authentication configuration (bearer token, client credentials)
- Connection preparation and client initialization
- Connection checking and validation
- Authentication token management

Test Strategy:
- Unit tests with mocked environment variables and clients
- Focus on load_fiware_params(), prepare_fiware_connection(), check_fiware_connection()
- All external dependencies (FILIP library, environment) are mocked
"""

# pylint: disable=protected-access, unused-argument, redefined-outer-name

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import os

from filip.clients.ngsi_v2 import ContextBrokerClient
from filip.models.base import FiwareHeaderSecure, DataType
from filip.models.ngsi_v2.base import NamedMetadata

from encodapy.config import ConfigModel, Interfaces
from encodapy.config.env_values import FiwareEnvVariables
from encodapy.service.communication.fiware_connection import FiwareConnection
from encodapy.utils.cratedb import CrateDBConnection
from encodapy.utils.error_handling import NoCredentials, InterfaceNotActive
from encodapy.utils.fiware_auth import BearerToken
from encodapy.utils.models import (
    FiwareAuth,
    FiwareConnectionParameter,
    FiwareParameter,
    DatabaseParameter,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_fiware_env_no_auth():
    """Create a mock FiwareEnvVariables with authentication disabled.
    
    Provides environment configuration where FIWARE authentication is turned off.
    Useful for testing scenarios where no authentication is required.
    
    Yields:
        FiwareEnvVariables: Mocked environment with auth=False and test service config.
    """
    with patch.dict(os.environ, {"FIWARE_AUTH": "false", "FIWARE_SERVICE": "test_service"}):
        env = FiwareEnvVariables()
        env.auth = False
        env.service = "test_service"
        env.service_path = "/test"
        env.cb_url = "http://localhost:1026"
        env.crate_db_url = "http://localhost:4200"
        yield env


@pytest.fixture
def mock_fiware_env_bearer_token():
    """Create a mock FiwareEnvVariables with bearer token authentication.
    
    Provides environment configuration for bearer token authentication mode.
    Useful for testing token-based authentication scenarios.
    
    Yields:
        FiwareEnvVariables: Mocked environment with auth=True and bearer token config.
    """
    with patch.dict(
        os.environ,
        {
            "FIWARE_AUTH": "true",
            "FIWARE_BEARER_TOKEN": "test_bearer_token",
            "FIWARE_SERVICE": "test_service",
            "FIWARE_CB_URL": "http://localhost:1026",
        },
    ):
        env = FiwareEnvVariables()
        env.auth = True
        env.bearer_token = "test_bearer_token"
        env.service = "test_service"
        env.service_path = "/test"
        env.cb_url = "http://localhost:1026"
        env.crate_db_url = "http://localhost:4200"
        yield env


@pytest.fixture
def mock_fiware_env_client_credentials():
    """Create a mock FiwareEnvVariables with client credentials authentication.
    
    Provides environment configuration for OAuth2 client credentials flow.
    Useful for testing authentication with client ID and secret.
    
    Yields:
        FiwareEnvVariables: Mocked environment with client credentials config.
    """
    with patch.dict(
        os.environ,
        {
            "FIWARE_AUTH": "true",
            "FIWARE_CLIENT_ID": "test_client",
            "FIWARE_CLIENT_PW": "test_password",
            "FIWARE_TOKEN_URL": "http://localhost:3000/token",
            "FIWARE_SERVICE": "test_service",
        },
    ):
        env = FiwareEnvVariables()
        env.auth = True
        env.client_id = "test_client"
        env.client_pw = "test_password"
        env.token_url = "http://localhost:3000/token"
        env.service = "test_service"
        env.service_path = "/test"
        env.cb_url = "http://localhost:1026"
        env.crate_db_url = "http://localhost:4200"
        yield env


@pytest.fixture
def mock_fiware_connection():
    """Create a FiwareConnection instance with mocked parameters.
    
    Provides a FiwareConnection with all connection parameters mocked using MagicMock.
    Useful for testing connection-related methods without actual network calls.
    
    Returns:
        FiwareConnection: Instance with mocked FIWARE and database parameters.
    """
    connection = FiwareConnection()
    connection.fiware_conn_params = MagicMock(spec=FiwareConnectionParameter)
    connection.fiware_conn_params.fiware_params = MagicMock(spec=FiwareParameter)
    connection.fiware_conn_params.fiware_params.authentication = None
    connection.fiware_conn_params.fiware_params.service = "test_service"
    connection.fiware_conn_params.fiware_params.service_path = "/test"
    connection.fiware_conn_params.fiware_params.cb_url = "http://localhost:1026"
    connection.fiware_conn_params.database_params = MagicMock(spec=DatabaseParameter)
    connection.fiware_conn_params.database_params.crate_db_url = "http://localhost:4200"
    connection.fiware_conn_params.database_params.crate_db_user = "test_user"
    connection.fiware_conn_params.database_params.crate_db_pw = "test_pw"
    connection.fiware_conn_params.database_params.crate_db_ssl = False
    return connection


@pytest.fixture
def mock_cb_client():
    """Create a mock ContextBrokerClient for testing.
    
    Provides a mocked FILIP ContextBrokerClient that returns test entity list.
    Useful for testing connection checking and entity operations.
    
    Returns:
        MagicMock: Mocked ContextBrokerClient with get_entity_list returning test data.
    """
    client = MagicMock(spec=ContextBrokerClient)
    client.get_entity_list.return_value = ["entity1", "entity2"]
    return client


@pytest.fixture
def mock_crate_db_client():
    """Create a mock CrateDBConnection for testing.
    
    Returns:
        MagicMock: Mocked CrateDBConnection instance.
    """
    return MagicMock(spec=CrateDBConnection)


# =============================================================================
# Tests for load_fiware_params
# =============================================================================


def test_load_fiware_params_no_auth(mock_fiware_env_no_auth):
    """Test loading FIWARE parameters with authentication disabled.
    
    Verifies that when FIWARE_AUTH is false, the connection parameters are loaded
    without authentication configuration.
    
    Args:
        mock_fiware_env_no_auth: Fixture providing environment with auth disabled
    
    Asserts:
        - fiware_conn_params is created
        - fiware_params is created
        - authentication is None (no auth configured)
        - service and service_path are correctly loaded
    """
    connection = FiwareConnection()
    
    with patch(
        "encodapy.service.communication.fiware_connection.FiwareEnvVariables",
        return_value=mock_fiware_env_no_auth,
    ):
        connection.load_fiware_params()
    
    assert connection.fiware_conn_params is not None
    assert connection.fiware_conn_params.fiware_params is not None
    assert connection.fiware_conn_params.fiware_params.authentication is None
    assert connection.fiware_conn_params.fiware_params.service == "test_service"
    assert connection.fiware_conn_params.fiware_params.service_path == "/test"


def test_load_fiware_params_bearer_token(mock_fiware_env_bearer_token):
    """Test loading FIWARE parameters with bearer token authentication.
    
    Verifies that bearer token authentication is correctly configured from
    environment variables.
    
    Args:
        mock_fiware_env_bearer_token: Fixture providing environment with bearer token
    
    Asserts:
        - fiware_conn_params is created
        - fiware_params is created
        - authentication is not None
        - bearer_token is correctly loaded
    """
    connection = FiwareConnection()
    
    with patch(
        "encodapy.service.communication.fiware_connection.FiwareEnvVariables",
        return_value=mock_fiware_env_bearer_token,
    ):
        connection.load_fiware_params()
    
    assert connection.fiware_conn_params is not None
    assert connection.fiware_conn_params.fiware_params is not None
    assert connection.fiware_conn_params.fiware_params.authentication is not None
    assert (
        connection.fiware_conn_params.fiware_params.authentication.bearer_token
        == "test_bearer_token"
    )


def test_load_fiware_params_client_credentials(mock_fiware_env_client_credentials):
    """Test loading FIWARE parameters with client credentials authentication.
    
    Verifies that OAuth2 client credentials are correctly loaded from environment
    variables.
    
    Args:
        mock_fiware_env_client_credentials: Fixture providing environment with client creds
    
    Asserts:
        - fiware_conn_params is created
        - fiware_params is created
        - authentication contains client_id, client_secret, and token_url
    """
    connection = FiwareConnection()
    
    with patch(
        "encodapy.service.communication.fiware_connection.FiwareEnvVariables",
        return_value=mock_fiware_env_client_credentials,
    ):
        connection.load_fiware_params()
    
    assert connection.fiware_conn_params is not None
    assert connection.fiware_conn_params.fiware_params is not None
    auth = connection.fiware_conn_params.fiware_params.authentication
    assert auth is not None
    assert auth.client_id == "test_client"
    assert auth.client_secret == "test_password"
    assert str(auth.token_url) == "http://localhost:3000/token"


def test_load_fiware_params_no_credentials_raises_error():
    """Test that NoCredentials is raised when auth is enabled but no credentials provided.
    
    Verifies error handling when authentication is required but no valid
    credentials (bearer token or client credentials) are available.
    
    Asserts:
        - NoCredentials exception is raised
    """
    with patch.dict(
        os.environ,
        {
            "FIWARE_AUTH": "true",
            "FIWARE_SERVICE": "test_service",
        },
    ):
        with patch(
            "encodapy.service.communication.fiware_connection.FiwareEnvVariables"
        ) as mock_env_class:
            mock_env = MagicMock()
            mock_env.auth = True
            mock_env.client_id = None
            mock_env.client_pw = None
            mock_env.token_url = None
            mock_env.bearer_token = None
            mock_env.service = "test_service"
            mock_env.service_path = "/test"
            mock_env.cb_url = "http://localhost:1026"
            mock_env.crate_db_url = "http://localhost:4200"
            mock_env_class.return_value = mock_env
            
            connection = FiwareConnection()
            
            with pytest.raises(NoCredentials):
                connection.load_fiware_params()


# =============================================================================
# Tests for check_fiware_connection
# =============================================================================


def test_check_fiware_connection_success(mock_fiware_connection, mock_cb_client):
    """Test checking FIWARE connection with entities available."""
    mock_fiware_connection.cb_client = mock_cb_client
    mock_cb_client.get_entity_list.return_value = ["entity1", "entity2"]
    
    # Should not raise an exception
    mock_fiware_connection.check_fiware_connection()


def test_check_fiware_connection_no_entities(mock_fiware_connection, mock_cb_client):
    """Test checking FIWARE connection with no entities available."""
    mock_fiware_connection.cb_client = mock_cb_client
    mock_cb_client.get_entity_list.return_value = []
    
    # Should not raise an exception, just log an error
    mock_fiware_connection.check_fiware_connection()
    
    # Verify that get_entity_list was called
    mock_cb_client.get_entity_list.assert_called_once()


def test_check_fiware_connection_no_client_raises_error(mock_fiware_connection):
    """Test that InterfaceNotActive is raised when client is not available."""
    mock_fiware_connection.cb_client = None
    
    with pytest.raises(InterfaceNotActive, match="ContextBrokerClient is not active"):
        mock_fiware_connection.check_fiware_connection()


# =============================================================================
# Tests for prepare_fiware_connection
# =============================================================================


def test_prepare_fiware_connection_no_auth(mock_fiware_connection, mock_cb_client, mock_crate_db_client):
    """Test preparing FIWARE connection without authentication."""
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = None
    
    with patch("encodapy.service.communication.fiware_connection.ContextBrokerClient") as mock_cbc:
        mock_instance = MagicMock()
        mock_cbc.return_value = mock_instance
        mock_instance.get_entity_list.return_value = ["entity1"]
        
        with patch("encodapy.service.communication.fiware_connection.CrateDBConnection") as mock_cdb:
            mock_cdb_instance = MagicMock()
            mock_cdb.return_value = mock_cdb_instance
            
            mock_fiware_connection.prepare_fiware_connection()
    
    assert mock_fiware_connection.cb_client is not None
    assert mock_fiware_connection.crate_db_client is not None
    assert mock_fiware_connection.fiware_token_client is None
    assert mock_fiware_connection.fiware_header is not None


def test_prepare_fiware_connection_with_bearer_token(mock_fiware_connection, mock_cb_client):
    """Test preparing FIWARE connection with bearer token authentication."""
    auth = FiwareAuth(bearer_token="test_token")
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = auth
    
    with patch("encodapy.service.communication.fiware_connection.BearerToken") as mock_bearer:
        mock_bearer_instance = MagicMock()
        mock_bearer_instance.bearer_token = "test_token"
        mock_bearer.return_value = mock_bearer_instance
        
        with patch("encodapy.service.communication.fiware_connection.ContextBrokerClient") as mock_cbc:
            mock_instance = MagicMock()
            mock_cbc.return_value = mock_instance
            mock_instance.get_entity_list.return_value = ["entity1"]
            
            with patch("encodapy.service.communication.fiware_connection.CrateDBConnection"):
                mock_fiware_connection.prepare_fiware_connection()
    
    assert mock_fiware_connection.fiware_token_client is not None
    assert mock_fiware_connection.fiware_header is not None
    assert mock_fiware_connection.fiware_header.__dict__["authorization"] == "test_token"
    assert mock_fiware_connection.cb_client is not None


def test_prepare_fiware_connection_with_client_credentials(mock_fiware_connection):
    """Test preparing FIWARE connection with client credentials authentication."""
    auth = FiwareAuth(
        client_id="test_client",
        client_secret="test_secret",
        token_url="http://localhost:3000/token",
    )
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = auth
    
    with patch("encodapy.service.communication.fiware_connection.BearerToken") as mock_bearer:
        mock_bearer_instance = MagicMock()
        mock_bearer_instance.bearer_token = "generated_token"
        mock_bearer.return_value = mock_bearer_instance
        
        with patch("encodapy.service.communication.fiware_connection.ContextBrokerClient") as mock_cbc:
            mock_instance = MagicMock()
            mock_cbc.return_value = mock_instance
            mock_instance.get_entity_list.return_value = ["entity1"]
            
            with patch("encodapy.service.communication.fiware_connection.CrateDBConnection"):
                mock_fiware_connection.prepare_fiware_connection()
    
    assert mock_fiware_connection.fiware_token_client is not None
    assert mock_fiware_connection.fiware_header is not None


# =============================================================================
# Tests for update_authentication
# =============================================================================


def test_update_authentication_refreshes_token(mock_fiware_connection):
    """Test that update_authentication refreshes the token when needed."""
    mock_token_client = MagicMock(spec=BearerToken)
    mock_token_client.check_token.return_value = False
    mock_token_client.bearer_token = "new_token"
    mock_fiware_connection.fiware_token_client = mock_token_client
    
    mock_header = MagicMock(spec=FiwareHeaderSecure)
    mock_header.__dict__ = {"authorization": "old_token"}
    mock_fiware_connection.fiware_header = mock_header
    
    auth = FiwareAuth(bearer_token="old_token")
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = auth
    
    mock_fiware_connection.update_authentication()
    
    assert mock_header.__dict__["authorization"] == "new_token"
    mock_token_client.check_token.assert_called_once()


def test_update_authentication_no_refresh_needed(mock_fiware_connection):
    """Test that update_authentication does nothing when token is valid."""
    mock_token_client = MagicMock(spec=BearerToken)
    mock_token_client.check_token.return_value = True
    mock_fiware_connection.fiware_token_client = mock_token_client
    
    mock_header = MagicMock(spec=FiwareHeaderSecure)
    mock_header.__dict__ = {"authorization": "valid_token"}
    mock_fiware_connection.fiware_header = mock_header
    
    auth = FiwareAuth(bearer_token="valid_token")
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = auth
    
    original_token = mock_header.__dict__["authorization"]
    mock_fiware_connection.update_authentication()
    
    # Token should not be updated if check_token returns True
    assert mock_header.__dict__["authorization"] == original_token
    mock_token_client.check_token.assert_called_once()


def test_update_authentication_no_auth(mock_fiware_connection):
    """Test that update_authentication handles no authentication gracefully."""
    mock_fiware_connection.fiware_conn_params.fiware_params.authentication = None
    mock_fiware_connection.fiware_token_client = None
    mock_fiware_connection.fiware_header = None
    
    # Should not raise an exception
    mock_fiware_connection.update_authentication()
