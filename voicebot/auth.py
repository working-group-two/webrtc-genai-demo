# Copyright (C) 2025 Cisco Systems, Inc.

import base64
import time

import grpc
import requests

from common import logger


class AccessTokenCallCredentials(grpc.AuthMetadataPlugin):
    """Custom AuthMetadataPlugin to fetch and refresh access tokens dynamically."""

    def __init__(self, client_id: str, client_secret: str):
        credentials = f"{client_id}:{client_secret}"
        self.basic_auth = base64.b64encode(credentials.encode()).decode()
        self.token = None
        self.token_expiry = 0

    def _fetch_access_token(self) -> None:
        """Fetch a new access token from the OAuth2 server."""
        url = "https://id.wgtwo.com/oauth2/token"
        headers = {
            "Authorization": f"Basic {self.basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "call.control.answer_and_initiate",
        }

        logger.info("Fetching new access token.")
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()

        if "access_token" not in token_data or "expires_in" not in token_data:
            raise RuntimeError("Invalid token response structure")

        self.token = token_data["access_token"]
        self.token_expiry = time.time() + token_data["expires_in"] - 60  # Refresh 1 minute before expiry
        logger.info("Access token fetched successfully.")

    def _get_valid_token(self) -> str:
        """Ensure a valid token is available, refreshing if necessary."""
        if not self.token or time.time() >= self.token_expiry:
            self._fetch_access_token()
        return self.token

    def __call__(self, context, callback):
        """Attach the token to the gRPC metadata."""
        try:
            token = self._get_valid_token()
            callback((("authorization", f"Bearer {token}"),), None)
        except Exception as e:
            logger.error(f"Failed to fetch access token: {e}")
            callback(None, grpc.RpcError(f"Failed to fetch access token: {e}"))
