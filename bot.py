import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.config import load_config
from app.db import init_db
from app.handlers.start import router as start_router
from app.handlers.booking import router as booking_router


async def main():
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    # DB init
    init_db(config.db_path)

    # routers
    dp.include_router(start_router)
    dp.include_router(booking_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
