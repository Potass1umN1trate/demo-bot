from __future__ import annotations

import json
import os
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service(credentials_path: str, token_path: str):
    logger.info("Getting Google Calendar service")
    creds = None

    if os.path.exists(token_path):
        logger.debug(f"Loading credentials from token file: {token_path}")
        with open(token_path, "r", encoding="utf-8") as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
        logger.debug("Token file loaded successfully")

    if not creds or not creds.valid:
        # refresh если можно
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            logger.info("Credentials refreshed successfully")
        else:
            # первый раз: интерактивная авторизация в браузере
            logger.info("Initiating OAuth2 flow for first-time authorization")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("OAuth2 authorization completed")

        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        logger.debug(f"Saving credentials to token file: {token_path}")
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        logger.debug("Credentials saved successfully")

    logger.info("Google Calendar service initialized")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)
