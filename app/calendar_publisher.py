from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
from zoneinfo import ZoneInfo

from app.repo import Repo, SERVICE_KEYS
from app.gcal_client import get_calendar_service

logger = logging.getLogger(__name__)


def parse_dt(date_str: str, time_str: str, tz: str) -> tuple[str, str]:
    """
    Возвращаем RFC3339 datetime strings для Calendar API.
    date_str: dd.MM.yyyy
    time_str: HH:mm
    tz: IANA, e.g. Europe/Moscow
    """
    dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    # Добавляем информацию о timezone
    tz_info = ZoneInfo(tz)
    dt_with_tz = dt.replace(tzinfo=tz_info)
    start = dt_with_tz.isoformat()
    end = (dt_with_tz + timedelta(hours=1)).isoformat()
    # Возвращаем для timeMin/timeMax (с timezone offset)
    # и для body start/end (также с timezone)
    return start, end


@dataclass
class CalendarPublisher:
    repo: Repo
    calendar_id: str
    credentials_path: str
    token_path: str
    tz: str

    def _service(self):
        return get_calendar_service(self.credentials_path, self.token_path)

    async def upsert_slot_event(self, service: str, date: str, time: str) -> str:
        """
        Создаёт или обновляет 1 событие на слот.
        Возвращает eventId.
        """
        logger.info(f"Upserting slot event for {service} on {date} at {time}")
        cap = await self.repo.get_capacity(service)
        bookings = await self.repo.get_active_bookings_for_slot(service, date, time)

        used = len(bookings)
        title = f"{service} {used}/{cap}"
        logger.debug(f"Slot title: {title}")

        participants = "\n".join([f"- {b.name} ({b.phone})" for b in bookings]) or "- (пока нет)"
        description = (
            "[RKBOOK]\n"
            f"Service: {service}\n"
            f"Slot: {date} {time}\n"
            f"Used: {used}/{cap}\n\n"
            "Participants:\n"
            f"{participants}\n"
        )

        start_iso, end_iso = parse_dt(date, time, self.tz)

        svc = self._service()

        # найти существующее событие по маркеру Slot: date time + service
        query = f"[RKBOOK] {service} {date} {time}"
        # Calendar API не ищет по description напрямую нормально; поэтому делаем грубее:
        # ищем события в окне 1 часа и фильтруем по description/summary.
        time_min = start_iso
        time_max = end_iso

        logger.debug(f"Searching for existing events in time range {time_min} to {time_max}")
        events = (
            svc.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
            )
            .execute()
            .get("items", [])
        )
        logger.debug(f"Found {len(events)} events in range")

        target = None
        for ev in events:
            desc = (ev.get("description") or "")
            summ = (ev.get("summary") or "")
            if desc.startswith("[RKBOOK]") and f"Slot: {date} {time}" in desc and f"Service: {service}" in desc:
                target = ev
                logger.debug(f"Found existing event with id={ev.get('id')}")
                break

        body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": self.tz},
            "end": {"dateTime": end_iso, "timeZone": self.tz},
        }

        if used == 0:
            # если никого нет — витринное событие удаляем (чтобы календарь был чистый)
            logger.info(f"No bookings in slot, deleting event if exists")
            if target and target.get("id"):
                logger.debug(f"Deleting event {target['id']}")
                svc.events().delete(calendarId=self.calendar_id, eventId=target["id"]).execute()
            return ""

        if target and target.get("id"):
            logger.info(f"Updating existing event {target['id']}")
            updated = (
                svc.events()
                .patch(calendarId=self.calendar_id, eventId=target["id"], body=body)
                .execute()
            )
            logger.info(f"Event updated successfully")
            return str(updated["id"])

        logger.info(f"Creating new calendar event")
        created = svc.events().insert(calendarId=self.calendar_id, body=body).execute()
        logger.info(f"Event created with id={created['id']}")
        return str(created["id"])
