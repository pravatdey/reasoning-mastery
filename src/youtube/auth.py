"""
YouTube Authentication - OAuth2 authentication for YouTube API
"""

import os
import json
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeAuth:
    """Handles OAuth2 authentication for YouTube Data API v3."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    def __init__(
        self,
        client_secrets_file: str = "config/client_secrets.json",
        token_file: str = "config/youtube_token.json"
    ):
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.credentials: Optional[Credentials] = None
        self.youtube = None
        logger.info("YouTubeAuth initialized")

    def authenticate(self) -> bool:
        try:
            self.credentials = self._load_credentials()

            if self.credentials and self.credentials.valid:
                return self._build_service()

            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    return self._build_service()
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")

            return self._new_authentication()

        except Exception as e:
            logger.error(f"Authentication failed: {e}", exc_info=True)
            return False

    def _load_credentials(self) -> Optional[Credentials]:
        env_token = os.environ.get('YOUTUBE_TOKEN_JSON')
        if env_token:
            token_data = self._parse_token_json(env_token, 'env')
            if token_data:
                return self._credentials_from_dict(token_data)

        token_path = Path(self.token_file)
        if not token_path.exists():
            return None

        try:
            with open(token_path, "r", encoding='utf-8-sig') as f:
                content = f.read()
            token_data = self._parse_token_json(content, self.token_file)
            if token_data:
                return self._credentials_from_dict(token_data)
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
        return None

    def _credentials_from_dict(self, token_data: dict) -> Optional[Credentials]:
        required = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
        if any(not token_data.get(f) for f in required):
            return None
        return Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes")
        )

    def _parse_token_json(self, content: str, source: str) -> Optional[dict]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(content.strip().lstrip('\ufeff'))
        except json.JSONDecodeError:
            pass
        try:
            import base64
            return json.loads(base64.b64decode(content.strip()).decode('utf-8'))
        except Exception:
            pass
        logger.error(f"Invalid JSON in {source}")
        return None

    def _save_credentials(self) -> None:
        token_path = Path(self.token_file)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_data = {
            "token": self.credentials.token,
            "refresh_token": self.credentials.refresh_token,
            "token_uri": self.credentials.token_uri,
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "scopes": self.credentials.scopes
        }
        with open(token_path, "w") as f:
            json.dump(token_data, f, indent=2)

    def _new_authentication(self) -> bool:
        if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
            logger.error("Cannot run OAuth flow in CI environment")
            return False

        secrets_path = Path(self.client_secrets_file)
        if not secrets_path.exists():
            logger.error(f"Client secrets not found: {self.client_secrets_file}")
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_path), scopes=self.SCOPES
            )
            self.credentials = flow.run_local_server(
                port=0, prompt="consent",
                success_message="Authentication successful! You can close this window."
            )
            self._save_credentials()
            return self._build_service()
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            return False

    def _build_service(self) -> bool:
        try:
            self.youtube = build("youtube", "v3", credentials=self.credentials)
            logger.info("YouTube API service built successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            return False

    def get_service(self):
        if not self.youtube:
            self.authenticate()
        return self.youtube

    def is_authenticated(self) -> bool:
        return self.credentials is not None and self.credentials.valid
