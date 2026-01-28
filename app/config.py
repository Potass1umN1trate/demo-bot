from dataclasses import dataclass
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int

    db_path: str

    gcal_calendar_id: str
    gcal_credentials_path: str
    gcal_token_path: str
    tz: str  

def load_config() -> Config:
    load_dotenv()
    
    logger.info("Loading configuration from environment variables")
    
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = int(os.getenv("ADMIN_ID", "0"))

    db_path = os.getenv("DB_PATH", "./data/demo_bot.sqlite3").strip()

    gcal_calendar_id = os.getenv("GCAL_CALENDAR_ID", "").strip()
    gcal_credentials_path = os.getenv("GCAL_CREDENTIALS_PATH", "./client_secret.json").strip()
    gcal_token_path = os.getenv("GCAL_TOKEN_PATH", "./tokens.json").strip()

    tz = os.getenv("TZ", "Belarus/Minsk").strip()

    if not bot_token:
        logger.error("BOT_TOKEN is missing")
        raise RuntimeError("BOT_TOKEN is missing")
    if admin_id == 0:
        logger.error("ADMIN_ID is missing or 0")
        raise RuntimeError("ADMIN_ID is missing or 0")
    if not gcal_calendar_id:
        logger.error("GCAL_CALENDAR_ID is missing")
        raise RuntimeError("GCAL_CALENDAR_ID is missing")

    logger.debug(f"Config loaded: db_path={db_path}, tz={tz}, admin_id={admin_id}")
    logger.info("Configuration loaded successfully")
    
    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        db_path=db_path,
        gcal_calendar_id=gcal_calendar_id,
        gcal_credentials_path=gcal_credentials_path,
        gcal_token_path=gcal_token_path,
        tz=tz,
    )
