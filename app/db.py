import os
import aiosqlite
import logging

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,          -- ISO datetime
  status TEXT NOT NULL,              -- active/cancelled
  service TEXT NOT NULL,
  date TEXT NOT NULL,                -- dd.MM.yyyy
  time TEXT NOT NULL,                -- HH:mm
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  tg_user_id TEXT,
  calendar_event_id TEXT             -- eventId from Google Calendar (for the slot event we manage)
);

CREATE TABLE IF NOT EXISTS services (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,         -- Service name (e.g., "🏓 Падел (групповая)")
  capacity INTEGER NOT NULL,         -- Max participants
  enabled BOOLEAN DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id TEXT NOT NULL UNIQUE,   -- Telegram user ID
  username TEXT,                     -- Telegram username
  is_owner BOOLEAN DEFAULT 0,        -- Only owner can manage admins
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_slot
ON bookings(service, date, time, status);

CREATE INDEX IF NOT EXISTS idx_bookings_phone
ON bookings(phone);

CREATE INDEX IF NOT EXISTS idx_admins_user_id
ON admins(tg_user_id);

"""

DEFAULT_SETTINGS = {
    "cap_padel_group": "3",
    "cap_padel_ind": "1",
    "cap_fitness": "10",
    "work_start_hour": "10",
    "work_end_hour": "22",
    "slot_minutes": "60",
}

async def init_db(db_path: str) -> None:
    logger.info(f"Initializing database at {db_path}")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        logger.debug("Executing database schema")
        await db.executescript(SCHEMA_SQL)

        # seed defaults if missing
        for k, v in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (k, v),
            )
            logger.debug(f"Set default setting: {k}={v}")

        await db.commit()
    
    logger.info("Database initialization completed")
