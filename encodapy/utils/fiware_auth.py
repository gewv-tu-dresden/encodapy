"""
Description: This file contains the class BearerToken,\
    which is used to check if an OAuth2 bearer token is valid.
Author: Martin Altenburger
"""

from typing import Optional
import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session


class BearerToken:
    """
    Checks if an OAuth2 bearer token is valid.

    Returns:
        bool: True, if token is valid
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_url: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.token = token
        if token is not None:
            self._token_typ = "static"
        else:
            self._token_typ = "limited"
        if self._token_typ == "limited":
            try:
                assert self.client_id is not None, \
                    "Client ID is required for limited token type"
                assert self.client_secret is not None, \
                    "Client secret is required for limited token type"
                assert self.token_url is not None, \
                    "Token URL is required for limited token type"
            except AssertionError as exc:
                raise ValueError("Missing required parameters for limited token type") from exc
            self._get_new_token()

    def _is_token_valid(
        self,
    ) -> bool:
        """
        Checks if an OAuth2 bearer token is valid.

        Returns:
            bool: True, if token is valid
        """
        if self._token_typ == "static":
            return True

        response = requests.get(
            url=f"""{self.token_url}/tokeninfo""",
            params={"access_token": self.token},
            timeout=10,
        )

        if response.status_code == 200:

            token_info = response.json()
            expires_in = token_info.get("expires_in")

            if expires_in is None or expires_in > 10:
                return True

        return False

    def _get_new_token(self) -> None:
        """
        Function to get new bearer-token from oauth2-provider
        """
        try:
            assert self.client_id is not None, \
                "Client ID is required to get a new token for limited token type"
            assert self.token_url is not None, \
                "Token URL is required to get a new token for limited token type"
        except AssertionError as exc:
            raise ValueError(
                "Missing required parameters to get a new token for limited token type"
                ) from exc

        client = BackendApplicationClient(client_id=self.client_id)
        oauth = OAuth2Session(client=client)
        self.token = oauth.fetch_token(
            token_url=self.token_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )["access_token"]

    @property
    def token_typ(self) -> str:
        """
        Returns the token type
        """
        return self._token_typ

    @property
    def bearer_token(self) -> str:
        """
        Returns the bearer-token
        """
        return f"""Bearer {self.token}"""

    def check_token(self) -> bool:
        """
        Function to check if the actual bearer-token is valid and if not,\
            get a new bearer-token from oauth2-provider

        Returns:
            bool: True if old token is valid, false if new token has been received
        """
        if self._is_token_valid():
            return True
        self._get_new_token()
        return False
