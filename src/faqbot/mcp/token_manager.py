"""
OAuth token manager for Notion MCP integration.

Handles OAuth token lifecycle including:
- Loading refresh tokens from configuration
- Exchanging refresh tokens for access tokens
- Automatic token refresh when expired
- Thread-safe token access
"""

import base64
import json
import logging
import threading
import time
import urllib.request as req
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class NotionTokenManager:
    """Manages OAuth tokens for Notion API access."""

    TOKEN_URL = "https://api.notion.com/v1/oauth/token"
    # Notion access tokens expire after 1 hour, refresh 5 minutes early
    TOKEN_EXPIRY_SECONDS = 3600
    REFRESH_BUFFER_SECONDS = 300

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ):
        """
        Initialize token manager.

        Args:
            client_id: Notion OAuth client ID
            client_secret: Notion OAuth client secret
            refresh_token: Notion OAuth refresh token (long-lived)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

        # Access token state
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._lock = threading.Lock()

        logger.info("NotionTokenManager initialized")

    def get_access_token(self) -> str:
        """
        Get current access token, refreshing if expired.

        Returns:
            Valid access token

        Raises:
            Exception: If token refresh fails
        """
        with self._lock:
            # Check if we need to refresh
            if self._needs_refresh():
                logger.info("Access token expired or missing, refreshing...")
                self._refresh_access_token()

            if not self._access_token:
                raise RuntimeError("Failed to obtain access token")

            return self._access_token

    def _needs_refresh(self) -> bool:
        """Check if token needs refresh."""
        if not self._access_token or not self._token_expiry:
            return True

        # Refresh if within buffer window of expiry
        time_until_expiry = (self._token_expiry - datetime.now()).total_seconds()
        return time_until_expiry < self.REFRESH_BUFFER_SECONDS

    def _refresh_access_token(self) -> None:
        """
        Refresh access token using refresh token.

        Raises:
            Exception: If token refresh fails
        """
        try:
            # Prepare request
            data = json.dumps({
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }).encode()

            # Create Basic Auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()

            # Make token refresh request
            request = req.Request(
                self.TOKEN_URL,
                data=data,
                method='POST',
                headers={
                    'Authorization': f'Basic {b64_credentials}',
                    'Content-Type': 'application/json'
                }
            )

            response = req.urlopen(request)
            result = json.loads(response.read().decode())

            # Extract new tokens
            if 'access_token' not in result:
                raise RuntimeError(f"No access_token in response: {result}")

            self._access_token = result['access_token']

            # Update refresh token if rotated
            if 'refresh_token' in result:
                logger.warning(
                    "Refresh token rotated - this needs to be updated in config! "
                    "New refresh token will be used temporarily but must be persisted."
                )
                self.refresh_token = result['refresh_token']

            # Calculate expiry time
            expires_in = result.get('expires_in', self.TOKEN_EXPIRY_SECONDS)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

            logger.info(
                f"Access token refreshed successfully, "
                f"expires at {self._token_expiry.isoformat()}"
            )

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            self._access_token = None
            self._token_expiry = None
            raise

    def force_refresh(self) -> None:
        """Force an immediate token refresh, ignoring expiry check."""
        with self._lock:
            logger.info("Forcing token refresh...")
            self._refresh_access_token()

    def clear_token(self) -> None:
        """Clear stored access token, forcing refresh on next access."""
        with self._lock:
            logger.info("Clearing stored access token")
            self._access_token = None
            self._token_expiry = None

    def get_token_info(self) -> dict:
        """
        Get information about current token state.

        Returns:
            Dictionary with token status information
        """
        with self._lock:
            if not self._access_token or not self._token_expiry:
                return {
                    "has_token": False,
                    "expired": True
                }

            time_until_expiry = (self._token_expiry - datetime.now()).total_seconds()

            return {
                "has_token": True,
                "expired": time_until_expiry <= 0,
                "expires_in_seconds": max(0, int(time_until_expiry)),
                "expires_at": self._token_expiry.isoformat()
            }
