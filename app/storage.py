import aiohttp
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SlotFullError(Exception):
    pass


class SheetStorage:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        logger.debug(f"SheetStorage initialized with base_url={base_url}")

    async def get_available_times(self, service: str, date_str: str) -> list[str]:
        logger.info(f"Fetching available times for {service} on {date_str}")
        params = {
            "action": "availability",
            "service": service,
            "date": date_str,
            "key": self.api_key,
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(self.base_url, params=params, timeout=15) as r:
                data = await r.json()
                if not data.get("ok"):
                    logger.error(f"Storage API error: {data}")
                    raise RuntimeError(data)
                logger.debug(f"Available times: {data['available_times']}")
                return data["available_times"]

    async def create_booking(self, payload: dict[str, Any]) -> int:
        logger.info(f"Creating booking via storage API: {payload}")
        body = {"action": "booking.create", "key": self.api_key, **payload}

        async with aiohttp.ClientSession() as s:
            async with s.post(self.base_url, json=body, timeout=20, allow_redirects=True) as r:
                ct = (r.headers.get("Content-Type") or "").lower()
                text = await r.text()

                # Если это не JSON — покажем кусок HTML, чтобы сразу понять что вернулось
                if "application/json" not in ct:
                    logger.error(
                        f"AppsScript returned non-JSON: status={r.status}, content-type={ct}, "
                        f"body_snippet={text[:400]!r}"
                    )
                    raise RuntimeError(
                        f"AppsScript returned non-JSON: status={r.status}, content-type={ct}, "
                        f"body_snippet={text[:400]!r}"
                    )

                data = json.loads(text)

                if data.get("ok"):
                    logger.info(f"Booking created with id={data['id']}")
                    return int(data["id"])
                if data.get("error") == "slot_full":
                    logger.warning("Slot is full")
                    raise SlotFullError()

                logger.error(f"AppsScript error: {data}")
                raise RuntimeError(f"AppsScript error: {data}")
