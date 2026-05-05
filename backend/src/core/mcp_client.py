"""Gmail client using Gmail API directly — no MCP protocol needed"""

import os
import base64
import logging
import tempfile
from email.mime.text import MIMEText
from typing import Any, List, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GMailMCPClient:
    """Gmail client — uses Gmail API directly."""

    def __init__(self):
        self.connected = False
        self._service = None
        self.get_configs()

    def get_configs(self):
        """Load Gmail API configurations from settings."""
        self.credentials_file = settings.gmail_credentials
        self.token_file = settings.gmail_tokens
        self.sender_email = settings.gmail_sender_email
        self.scopes = settings.gmail_scopes
        self.impersonated_user = settings.gmail_impersonated_user
        self.credentials_b64 = settings.gmail_credentials_b64
        self.tokens_b64 = settings.gmail_token_b64

    async def connect(self):
        """Authenticate with Gmail API."""
        try:

            creds = None

            if self.tokens_b64:
                tokens_json = base64.b64decode(self.tokens_b64).decode()
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    f.write(tokens_json)
                    tmp_token = f.name
                creds = Credentials.from_authorised_user_file(tmp_token, self.scopes)
                os.unlink(tmp_token)
            elif os.path.exists(self.token_file):
                creds = Credentials.from_authorised_user_file(
                    self.token_file, self.scopes
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if self.credentials_b64:
                        creds_json = base64.b64decode(self.credentials_b64).decode()
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".json", delete=False
                        ) as f:
                            f.write(creds_json)
                            tmp_creds = f.name
                        flow = InstalledAppFlow.from_client_secrets_file(
                            tmp_creds, self.scopes
                        )
                        os.unlink(tmp_creds)
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.scopes
                        )

                    creds = flow.run_local_server(
                        port=0, access_type="offline", prompt="consent"
                    )
                    with open(self.token_file, "w") as token:
                        token.write(creds.to_json())

            self._service = build("gmail", "v1", credentials=creds)
            self.connected = True
            logger.info("Connected to Gmail API")
        except Exception as e:
            logger.error("Failed to connect to Gmail API: %s", e)
            raise

    async def send_email(
        self, to_email: str, subject: str, body: str
    ) -> Dict[str, Any]:
        """Send email via Gmail API."""
        if not self.connected:
            await self.connect()

        message = MIMEText(body, "html")
        message["to"] = to_email
        message["subject"] = subject
        message["from"] = self.sender_email

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        result = (
            self._service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )

        return {
            "success": True,
            "message_id": result["id"],
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

    async def read_emails(
        self, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search and read emails via Gmail API."""
        if not self.connected:
            await self.connect()

        results = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            msg_data = (
                self._service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )

            headers = {
                h["name"]: h["value"] for h in msg_data["payload"].get("headers", [])
            }

            body = ""
            payload = msg_data.get("payload", {})
            parts = payload.get("parts", [])
            if parts:
                for part in parts:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data", "")
                        body = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                        break
            elif payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                    "utf-8", errors="ignore"
                )

            emails.append(
                {
                    "id": msg["id"],
                    "subject": headers.get("Subject", ""),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "body": body,
                }
            )

        return emails
