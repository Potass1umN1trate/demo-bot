from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def start_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📅 Записаться на тренировку")]],
        resize_keyboard=True
    )


def services_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏓 Падел (групповая)", callback_data="service:paddle_group")
    kb.button(text="🏓 Падел (индивидуальная)", callback_data="service:paddle_ind")
    kb.button(text="🏋️ Фитнес", callback_data="service:fitness")
    kb.adjust(1)
    return kb.as_markup()


def date_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Сегодня", callback_data="date:today")
    kb.button(text="Завтра", callback_data="date:tomorrow")
    kb.button(text="Выбрать дату", callback_data="date:pick")
    kb.adjust(2, 1)
    return kb.as_markup()


def time_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in ["10:00", "11:00", "12:00"]:
        kb.button(text=t, callback_data=f"time:{t}")
    kb.adjust(3)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="confirm:yes")
    kb.button(text="❌ Отменить", callback_data="confirm:no")
    kb.adjust(2)
    return kb.as_markup()
