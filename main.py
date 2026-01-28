import asyncio
import os
from aiogram import Bot, Dispatcher

from app.config import load_config
from app.db import init_db
from app.repo import Repo
from app.calendar_publisher import CalendarPublisher
from app.logger import setup_logger
from app.handlers import start, booking, admin

from dotenv import load_dotenv
load_dotenv()

# Configure root logger so all modules inherit the configuration
logger = setup_logger("root", os.getenv("LOG_LEVEL", "INFO"))

async def main():
    logger.info("Starting bot initialization...")
    config = load_config()
    logger.debug(f"Config loaded: calendar_id={config.gcal_calendar_id[:20]}..., db={config.db_path}")
    
    await init_db(config.db_path)
    logger.info("Database initialized")

    bot = Bot(token=config.bot_token)
    logger.info("Bot instance created")
    logger.debug(f"Bot token: {config.bot_token[:10]}...")
    
    dp = Dispatcher()
    logger.debug("Dispatcher created")

    repo = Repo(config.db_path)
    logger.debug("Repository initialized")
    
    # Initialize owner admin
    owner_admin_id = str(config.owner_admin_id)
    if not await repo.is_admin(owner_admin_id):
        logger.info(f"Initializing owner admin: {owner_admin_id}")
        await repo.add_admin(owner_admin_id, is_owner=True)
    
    publisher = CalendarPublisher(
        repo=repo,
        calendar_id=config.gcal_calendar_id,
        credentials_path=config.gcal_credentials_path,
        token_path=config.gcal_token_path,
        tz=config.tz,
    )
    logger.debug(f"Calendar publisher initialized with timezone: {config.tz}")

    # сюда подключишь роутеры, и в зависимости от твоей реализации
    # прокинь repo/publisher через dp["repo"]=repo или через DI/closure
    # например:
    dp["repo"] = repo
    dp["publisher"] = publisher
    dp["config"] = config
    logger.debug("Dependencies injected into dispatcher")

    # include routers...
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(admin.router)
    logger.debug("Routers registered")

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error during polling: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
