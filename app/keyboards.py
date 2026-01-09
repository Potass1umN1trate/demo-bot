from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta

RU_DOW = {
    "Mon": "Пн", "Tue": "Вт", "Wed": "Ср", "Thu": "Чт",
    "Fri": "Пт", "Sat": "Сб", "Sun": "Вс",
}

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

def date_pick_kb(days: int = 7, start_from_tomorrow: bool = True) -> InlineKeyboardMarkup:
    """
    Мини-календарь на N дней.
    callback_data: datepick:YYYY-MM-DD
    """
    start = date.today() + timedelta(days=1 if start_from_tomorrow else 0)

    kb = InlineKeyboardBuilder()
    for i in range(days):
        d = start + timedelta(days=i)
        # Читабельный текст на кнопке: "Пн 12.01"
        dow = d.strftime("%a")  # Mon
        label = f"{RU_DOW.get(dow, dow)} {d.strftime('%d.%m')}"
        # Если хочешь русские дни недели — ниже сделаем маппинг (не обязательно)
        kb.button(text=label, callback_data=f"datepick:{d.isoformat()}")

    # 2 ряда (4 + 3) выглядят аккуратно
    kb.adjust(4, 3)

    # Кнопка назад — чтобы не было тупика
    kb.button(text="⬅️ Назад", callback_data="date:back")
    kb.adjust(4, 3, 1)

    return kb.as_markup()
