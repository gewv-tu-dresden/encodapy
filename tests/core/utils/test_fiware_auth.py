"""Tests for the OAuth2 bearer token handling in encodapy.utils.fiware_auth.

All network access (token info endpoint and OAuth2 token fetch) is mocked,
so these tests run fully offline.
"""

# pylint: disable=protected-access
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from encodapy.utils import fiware_auth
from encodapy.utils.fiware_auth import BearerToken


class FakeTokenResponse:  # pylint: disable=too-few-public-methods
    """Minimal stand-in for a requests.Response of the tokeninfo endpoint."""

    def __init__(self, status_code: int, payload: dict[str, Any] | None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        """Return the payload of the fake tokeninfo response."""
        if self._payload is None:
            raise ValueError("No payload")
        return self._payload


@pytest.fixture
def patched_oauth_session() -> Iterator[MagicMock]:
    """Patch OAuth2Session so that no token request is performed."""
    with patch.object(fiware_auth, "OAuth2Session") as mock:
        session = MagicMock()
        session.fetch_token.return_value = {"access_token": "fetched-token"}
        mock.return_value = session
        yield mock


def make_limited_token(**kwargs: Any) -> BearerToken:
    """Create a limited bearer token with default parameters."""
    defaults: dict[str, str] = {
        "client_id": "client",
        "client_secret": "secret",
        "token_url": "https://auth.example.com",
    }
    defaults.update(kwargs)
    return BearerToken(**defaults)


class TestBearerTokenStatic:
    """Tests for the static token type."""

    def test_static_token_type(self) -> None:
        """A given token results in the static token type."""
        token = BearerToken(token="static-token")

        assert token.token_typ == "static"
        assert token.token == "static-token"

    def test_bearer_token_property(self) -> None:
        """The bearer_token property prefixes the token with 'Bearer '."""
        token = BearerToken(token="static-token")

        assert token.bearer_token == "Bearer static-token"

    def test_static_token_is_always_valid(self) -> None:
        """A static token is valid without any endpoint request."""
        token = BearerToken(token="static-token")

        with patch.object(fiware_auth.requests, "get") as mock_get:
            assert token._is_token_valid() is True
            mock_get.assert_not_called()

    def test_check_token_returns_true_for_static_token(self) -> None:
        """check_token returns True for a static token without refresh."""
        token = BearerToken(token="static-token")

        with patch.object(fiware_auth.requests, "get") as mock_get:
            assert token.check_token() is True
            mock_get.assert_not_called()


@pytest.mark.usefixtures("patched_oauth_session")
class TestBearerTokenLimited:
    """Tests for the limited token type (token fetched from an OAuth2 provider)."""

    def test_limited_token_fetches_token_on_init(
        self,
        patched_oauth_session: MagicMock,  # pylint: disable=redefined-outer-name
    ) -> None:
        """The limited token type fetches a new token during initialization."""
        token = make_limited_token()

        assert token.token_typ == "limited"
        assert token.token == "fetched-token"
        patched_oauth_session.return_value.fetch_token.assert_called_once_with(
            token_url="https://auth.example.com",
            client_id="client",
            client_secret="secret",
        )

    def test_missing_client_id_raises_value_error(self) -> None:
        """A missing client id raises a ValueError."""
        with pytest.raises(ValueError, match="Missing required parameters"):
            make_limited_token(client_id=None)

    def test_missing_client_secret_raises_value_error(self) -> None:
        """A missing client secret raises a ValueError."""
        with pytest.raises(ValueError, match="Missing required parameters"):
            make_limited_token(client_secret=None)

    def test_missing_token_url_raises_value_error(self) -> None:
        """A missing token url raises a ValueError."""
        with pytest.raises(ValueError, match="Missing required parameters"):
            make_limited_token(token_url=None)

    def test_get_new_token_without_client_id_raises_value_error(self) -> None:
        """_get_new_token raises a ValueError if the client id is removed."""
        token = make_limited_token()
        token.client_id = None

        with pytest.raises(
            ValueError, match="Missing required parameters to get a new token"
        ):
            token._get_new_token()

    def test_get_new_token_without_token_url_raises_value_error(self) -> None:
        """_get_new_token raises a ValueError if the token url is removed."""
        token = make_limited_token()
        token.token_url = None

        with pytest.raises(
            ValueError, match="Missing required parameters to get a new token"
        ):
            token._get_new_token()

    def test_bearer_token_property_uses_fetched_token(self) -> None:
        """The bearer_token property uses the fetched token."""
        token = make_limited_token()

        assert token.bearer_token == "Bearer fetched-token"


@pytest.mark.usefixtures("patched_oauth_session")
class TestTokenValidation:
    """Tests for the validation of the limited token against the tokeninfo endpoint."""

    def _token_with_response(
        self, response: FakeTokenResponse
    ) -> tuple[BearerToken, MagicMock]:
        token = make_limited_token()
        get_mock = MagicMock(return_value=response)
        return token, get_mock

    def test_valid_token_with_expiry(self) -> None:
        """A 200 response with a large expires_in value validates the token."""
        response = FakeTokenResponse(200, {"expires_in": 100})
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token._is_token_valid() is True

        get_mock.assert_called_once_with(
            url="https://auth.example.com/tokeninfo",
            params={"access_token": "fetched-token"},
            timeout=10,
        )

    def test_valid_token_without_expiry_information(self) -> None:
        """A 200 response without expires_in validates the token."""
        response = FakeTokenResponse(200, {})
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token._is_token_valid() is True

    def test_token_expiring_soon_is_invalid(self) -> None:
        """An expires_in value of 10 or less invalidates the token."""
        response = FakeTokenResponse(200, {"expires_in": 10})
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token._is_token_valid() is False

    def test_error_response_invalidates_token(self) -> None:
        """A non 200 response invalidates the token."""
        response = FakeTokenResponse(401, None)
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token._is_token_valid() is False

    def test_check_token_returns_true_for_valid_token(
        self,
        patched_oauth_session: MagicMock,  # pylint: disable=redefined-outer-name
    ) -> None:
        """check_token returns True and does not fetch a new token."""
        response = FakeTokenResponse(200, {"expires_in": 100})
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token.check_token() is True

        patched_oauth_session.return_value.fetch_token.assert_called_once()

    def test_check_token_refreshes_invalid_token(
        self,
        patched_oauth_session: MagicMock,  # pylint: disable=redefined-outer-name
    ) -> None:
        """check_token fetches a new token if the old one is invalid."""
        response = FakeTokenResponse(200, {"expires_in": 5})
        token, get_mock = self._token_with_response(response)

        with patch.object(fiware_auth.requests, "get", get_mock):
            assert token.check_token() is False

        assert token.token == "fetched-token"
        assert patched_oauth_session.return_value.fetch_token.call_count == 2
