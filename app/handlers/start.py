from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards import start_kb
from app.texts import WELCOME

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=start_kb())
