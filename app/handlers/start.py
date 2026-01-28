from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
import logging

from app.keyboards import start_kb
from app.texts import WELCOME

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"User {user_id} (@{username}) sent /start command")
    logger.debug(f"User profile: {message.from_user}")
    await message.answer(WELCOME, reply_markup=start_kb())
    logger.debug(f"Welcome message sent to user {user_id}")
