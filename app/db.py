import sqlite3
from typing import Dict, Any


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now')),
        user_id INTEGER NOT NULL,
        service TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def insert_booking(db_path: str, booking: Dict[str, Any]) -> int:
    """
    booking keys: user_id, service, date, time, name, phone
    Returns inserted row id.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO bookings (user_id, service, date, time, name, phone)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        booking["user_id"],
        booking["service"],
        booking["date"],
        booking["time"],
        booking["name"],
        booking["phone"],
    ))

    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id
