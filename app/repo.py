from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence
import logging

import aiosqlite

logger = logging.getLogger(__name__)


class SlotFullError(Exception):
    pass


@dataclass(frozen=True)
class Booking:
    id: int
    status: str
    service: str
    date: str
    time: str
    name: str
    phone: str
    tg_user_id: Optional[str]
    calendar_event_id: Optional[str]


SERVICE_KEYS = {
    "🏓 Падел (групповая)": "cap_padel_group",
    "🏓 Падел (индивидуальная)": "cap_padel_ind",
    "🏋️ Фитнес": "cap_fitness",
}


class Repo:
    def __init__(self, db_path: str):
        self.db_path = db_path
        logger.debug(f"Repo initialized with db_path={db_path}")

    async def _get_setting(self, key: str) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            if not row:
                logger.error(f"Missing setting: {key}")
                raise RuntimeError(f"Missing setting: {key}")
            logger.debug(f"Retrieved setting {key}={row['value']}")
            return str(row["value"])

    async def get_capacity(self, service: str) -> int:
        k = SERVICE_KEYS.get(service)
        if not k:
            logger.error(f"Unknown service: {service}")
            raise RuntimeError(f"Unknown service: {service}")
        capacity = int(await self._get_setting(k))
        logger.debug(f"Service '{service}' capacity: {capacity}")
        return capacity

    async def get_slot_params(self) -> tuple[int, int, int]:
        start = int(await self._get_setting("work_start_hour"))
        end = int(await self._get_setting("work_end_hour"))
        slot_minutes = int(await self._get_setting("slot_minutes"))
        logger.debug(f"Slot params: {start}:00-{end}:00, slot_minutes={slot_minutes}")
        return start, end, slot_minutes

    async def count_active(self, service: str, date: str, time: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM bookings WHERE status='active' AND service=? AND date=? AND time=?",
                (service, date, time),
            )
            row = await cursor.fetchone()
            count = int(row[0]) if row else 0
            logger.debug(f"Active bookings for {service} on {date} at {time}: {count}")
            return count

    async def get_available_times(self, service: str, date: str) -> list[str]:
        logger.info(f"Getting available times for {service} on {date}")
        cap = await self.get_capacity(service)
        logger.debug(f"Slot capacity: {cap}")
        
        start_hour, end_hour, slot_minutes = await self.get_slot_params()
        logger.debug(f"Working hours: {start_hour}:00 - {end_hour}:00, slot duration: {slot_minutes} minutes")

        # для демо: слоты только по часу, но оставим slot_minutes на будущее
        if slot_minutes != 60:
            logger.error(f"Only 60-minute slots supported, got {slot_minutes}")
            raise RuntimeError("Only 60-minute slots supported in this MVP")

        all_times = [f"{h:02d}:00" for h in range(start_hour, end_hour + 1)]
        logger.debug(f"All time slots: {all_times}")
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT time, COUNT(*) as cnt
                FROM bookings
                WHERE status='active' AND service=? AND date=?
                GROUP BY time
                """,
                (service, date),
            )
            rows = await cursor.fetchall()
            busy = {str(r["time"]): int(r["cnt"]) for r in rows}
            logger.debug(f"Current bookings: {busy}")

        available = [t for t in all_times if busy.get(t, 0) < cap]
        logger.info(f"Available times for {service} on {date}: {available} ({len(available)} slots)")
        return available

    async def create_booking(
        self,
        *,
        service: str,
        date: str,
        time: str,
        name: str,
        phone: str,
        tg_user_id: Optional[str],
    ) -> int:
        logger.info(f"Creating booking: {service} on {date} at {time} for {name} ({phone}), tg_user_id={tg_user_id}")
        # делаем атомарно: проверка вместимости + insert под транзакцией
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("BEGIN IMMEDIATE")  # блокируем на запись
            logger.debug("Started transaction for booking creation")
            cap = await self.get_capacity(service)

            cursor = await db.execute(
                "SELECT COUNT(*) FROM bookings WHERE status='active' AND service=? AND date=? AND time=?",
                (service, date, time),
            )
            row = await cursor.fetchone()
            cnt = int(row[0]) if row else 0
            logger.debug(f"Current bookings in slot: {cnt}/{cap}")
            if cnt >= cap:
                logger.warning(f"Slot full for {service} on {date} at {time} (capacity: {cap})")
                await db.execute("ROLLBACK")
                raise SlotFullError()

            now = datetime.utcnow().isoformat(timespec="seconds")
            cur = await db.execute(
                """
                INSERT INTO bookings(created_at, status, service, date, time, name, phone, tg_user_id, calendar_event_id)
                VALUES(?, 'active', ?, ?, ?, ?, ?, ?, NULL)
                """,
                (now, service, date, time, name, phone, tg_user_id),
            )
            booking_id = int(cur.lastrowid)
            await db.commit()
            logger.info(f"Booking created successfully with id={booking_id}")
            return booking_id

    async def cancel_booking(self, booking_id: int) -> None:
        logger.info(f"Cancelling booking id={booking_id}")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT service, date, time FROM bookings WHERE id=?",
                (booking_id,),
            )
            row = await cursor.fetchone()
            if row:
                logger.debug(f"Booking {booking_id}: {row[0]} on {row[1]} at {row[2]}")
            
            await db.execute(
                "UPDATE bookings SET status='cancelled' WHERE id=?",
                (booking_id,),
            )
            await db.commit()
        logger.info(f"Booking id={booking_id} cancelled successfully")

    async def attach_event_id_for_slot(self, service: str, date: str, time: str, event_id: str) -> None:
        logger.debug(f"Attaching event_id={event_id} to slot {service} on {date} at {time}")
        # сохраняем event_id в записях этого слота (чтобы потом можно было найти/обновить)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE bookings
                SET calendar_event_id=?
                WHERE status='active' AND service=? AND date=? AND time=?
                """,
                (event_id, service, date, time),
            )
            await db.commit()
            rows_affected = cursor.rowcount
            logger.debug(f"Event_id attached to {rows_affected} booking(s)")

    async def get_active_bookings_for_slot(self, service: str, date: str, time: str) -> list[Booking]:
        logger.debug(f"Fetching active bookings for {service} on {date} at {time}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, status, service, date, time, name, phone, tg_user_id, calendar_event_id
                FROM bookings
                WHERE status='active' AND service=? AND date=? AND time=?
                ORDER BY id ASC
                """,
                (service, date, time),
            )
            rows = await cursor.fetchall()
            bookings = [
                Booking(
                    id=int(r["id"]),
                    status=str(r["status"]),
                    service=str(r["service"]),
                    date=str(r["date"]),
                    time=str(r["time"]),
                    name=str(r["name"]),
                    phone=str(r["phone"]),
                    tg_user_id=str(r["tg_user_id"]) if r["tg_user_id"] is not None else None,
                    calendar_event_id=str(r["calendar_event_id"]) if r["calendar_event_id"] is not None else None,
                )
                for r in rows
            ]
            logger.debug(f"Found {len(bookings)} active bookings for slot")
            return bookings
    # Admin Methods
    async def is_admin(self, tg_user_id: str) -> bool:
        logger.debug(f"Checking if user {tg_user_id} is admin")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM admins WHERE tg_user_id=?",
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            is_admin_user = row is not None
            logger.debug(f"User {tg_user_id} is_admin: {is_admin_user}")
            return is_admin_user

    async def is_owner(self, tg_user_id: str) -> bool:
        logger.debug(f"Checking if user {tg_user_id} is owner")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT is_owner FROM admins WHERE tg_user_id=?",
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            is_owner_user = row is not None and bool(row[0])
            logger.debug(f"User {tg_user_id} is_owner: {is_owner_user}")
            return is_owner_user

    async def add_admin(self, tg_user_id: str, username: Optional[str] = None, is_owner: bool = False) -> None:
        logger.info(f"Adding admin: tg_user_id={tg_user_id}, username={username}, is_owner={is_owner}")
        now = datetime.utcnow().isoformat(timespec="seconds")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins(tg_user_id, username, is_owner, created_at) VALUES(?, ?, ?, ?)",
                (tg_user_id, username, int(is_owner), now),
            )
            await db.commit()
        logger.info(f"Admin added successfully: {tg_user_id}")

    async def remove_admin(self, tg_user_id: str) -> None:
        logger.info(f"Removing admin: tg_user_id={tg_user_id}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM admins WHERE tg_user_id=?", (tg_user_id,))
            await db.commit()
        logger.info(f"Admin removed successfully: {tg_user_id}")

    async def get_all_admins(self) -> list[tuple[str, Optional[str], bool]]:
        logger.debug("Fetching all admins")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT tg_user_id, username, is_owner FROM admins ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            admins = [(str(r[0]), r[1], bool(r[2])) for r in rows]
            logger.debug(f"Found {len(admins)} admins")
            return admins

    # Service Management
    async def get_all_services(self) -> list[tuple[int, str, int, bool]]:
        logger.debug("Fetching all services")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, capacity, enabled FROM services ORDER BY name"
            )
            rows = await cursor.fetchall()
            services = [(int(r[0]), str(r[1]), int(r[2]), bool(r[3])) for r in rows]
            logger.debug(f"Found {len(services)} services")
            return services

    async def add_service(self, name: str, capacity: int) -> int:
        logger.info(f"Adding service: name={name}, capacity={capacity}")
        now = datetime.utcnow().isoformat(timespec="seconds")
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO services(name, capacity, enabled, created_at) VALUES(?, ?, 1, ?)",
                (name, capacity, now),
            )
            await db.commit()
            service_id = int(cursor.lastrowid)
        logger.info(f"Service added: id={service_id}")
        return service_id

    async def update_service(self, service_id: int, name: Optional[str] = None, capacity: Optional[int] = None) -> None:
        logger.info(f"Updating service {service_id}: name={name}, capacity={capacity}")
        if name is not None:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE services SET name=? WHERE id=?", (name, service_id))
                await db.commit()
        if capacity is not None:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE services SET capacity=? WHERE id=?", (capacity, service_id))
                await db.commit()
        logger.info(f"Service {service_id} updated")

    async def delete_service(self, service_id: int) -> None:
        logger.info(f"Deleting service {service_id}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM services WHERE id=?", (service_id,))
            await db.commit()
        logger.info(f"Service {service_id} deleted")

    # Booking Management
    async def get_all_bookings(self, limit: int = 50) -> list[Booking]:
        logger.debug(f"Fetching all bookings (limit={limit})")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, status, service, date, time, name, phone, tg_user_id, calendar_event_id
                FROM bookings
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            bookings = [
                Booking(
                    id=int(r["id"]),
                    status=str(r["status"]),
                    service=str(r["service"]),
                    date=str(r["date"]),
                    time=str(r["time"]),
                    name=str(r["name"]),
                    phone=str(r["phone"]),
                    tg_user_id=str(r["tg_user_id"]) if r["tg_user_id"] is not None else None,
                    calendar_event_id=str(r["calendar_event_id"]) if r["calendar_event_id"] is not None else None,
                )
                for r in rows
            ]
            logger.debug(f"Found {len(bookings)} bookings")
            return bookings

    async def get_booking_by_id(self, booking_id: int) -> Optional[Booking]:
        logger.debug(f"Fetching booking {booking_id}")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT id, status, service, date, time, name, phone, tg_user_id, calendar_event_id
                FROM bookings
                WHERE id=?
                """,
                (booking_id,),
            )
            row = await cursor.fetchone()
            if not row:
                logger.debug(f"Booking {booking_id} not found")
                return None
            booking = Booking(
                id=int(row["id"]),
                status=str(row["status"]),
                service=str(row["service"]),
                date=str(row["date"]),
                time=str(row["time"]),
                name=str(row["name"]),
                phone=str(row["phone"]),
                tg_user_id=str(row["tg_user_id"]) if row["tg_user_id"] is not None else None,
                calendar_event_id=str(row["calendar_event_id"]) if row["calendar_event_id"] is not None else None,
            )
            logger.debug(f"Found booking {booking_id}")
            return booking

    async def update_booking(self, booking_id: int, name: Optional[str] = None, phone: Optional[str] = None) -> None:
        logger.info(f"Updating booking {booking_id}: name={name}, phone={phone}")
        if name is not None:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE bookings SET name=? WHERE id=?", (name, booking_id))
                await db.commit()
        if phone is not None:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE bookings SET phone=? WHERE id=?", (phone, booking_id))
                await db.commit()
        logger.info(f"Booking {booking_id} updated")