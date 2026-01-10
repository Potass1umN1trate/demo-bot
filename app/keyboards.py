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

def _fmt_day_button(d: date) -> str:
    dow = RU_DOW.get(d.strftime("%a"), d.strftime("%a"))
    return f"{dow} {d.strftime('%d.%m')}"


def week_picker_kb(page: int = 0, weeks_ahead: int = 3) -> InlineKeyboardMarkup:
    """
    Календарь по неделям:
    - page=0: текущая неделя (сегодня..вс)
    - page=1..weeks_ahead: полные недели (пн..вс)
    Всего страниц: 0..weeks_ahead
    """
    if page < 0:
        page = 0
    if page > weeks_ahead:
        page = weeks_ahead

    today = date.today()

    # Находим понедельник текущей недели
    this_monday = today - timedelta(days=today.weekday())  # weekday: Mon=0..Sun=6

    if page == 0:
        start = today
        # воскресенье текущей недели
        end = this_monday + timedelta(days=6)
    else:
        start = this_monday + timedelta(days=7 * page)
        end = start + timedelta(days=6)

    kb = InlineKeyboardBuilder()

    # дни недели
    d = start
    while d <= end:
        kb.button(text=_fmt_day_button(d), callback_data=f"datepick:{d.isoformat()}")
        d += timedelta(days=1)

    # на первой странице может быть 1..7 дней; на остальных всегда 7
    # разложение по рядам выглядит аккуратно:
    # - если 4-7 кнопок: 4 + остаток
    # - если 1-3 кнопки: 3
    count = (end - start).days + 1
    if count >= 7:
        kb.adjust(4, 3)
    elif count == 6:
        kb.adjust(3, 3)
    elif count == 5:
        kb.adjust(3, 2)
    elif count == 4:
        kb.adjust(2, 2)
    else:
        kb.adjust(3)

    # навигация
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️ Пред. неделя", callback_data=f"week:{page-1}")
    if page < weeks_ahead:
        nav.button(text="След. неделя ➡️", callback_data=f"week:{page+1}")

    # кнопка "назад к простому выбору"
    nav.button(text="⬅️ Назад", callback_data="date:back")

    # навигацию делаем одной строкой (сколько влезет)
    nav.adjust(2, 1)  # может получиться: [prev, next] и потом [back]
    for row in nav.export():
        kb.row(*row)

    return kb.as_markup()