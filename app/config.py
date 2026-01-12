import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_id: int
    db_path: str = "bookings.sqlite3"
    gscript_url: str = ""
    gscript_key: str = ""

def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    admin_id = os.getenv("ADMIN_ID")
    gscript_url = os.getenv("GSCRIPT_URL", "")
    gscript_key = os.getenv("GSCRIPT_KEY", "")

    if not token:
        raise RuntimeError("BOT_TOKEN is missing in .env")
    if not admin_id:
        raise RuntimeError("ADMIN_ID is missing in .env")

    return Config(
        bot_token=token,
        admin_id=int(admin_id),
        gscript_url=gscript_url,
        gscript_key=gscript_key,
    )
