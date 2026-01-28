from datetime import date, timedelta
import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.states import BookingFlow
from app.keyboards import services_kb, date_kb, time_kb, confirm_kb, week_picker_kb
from app.texts import (
    ASK_SERVICE, ASK_DATE, ASK_TIME, ASK_NAME, ASK_PHONE,
    CONFIRM_TEMPLATE, BOOKED_USER, CANCELLED
)
from app.config import load_config

from app.repo import Repo, SlotFullError
from app.calendar_publisher import CalendarPublisher

logger = logging.getLogger(__name__)

router = Router()

# Для демо можно держать singleton'ы на процесс (как у тебя было)
config = load_config()
repo = Repo(config.db_path)
publisher = CalendarPublisher(
    repo=repo,
    calendar_id=config.gcal_calendar_id,
    credentials_path=config.gcal_credentials_path,
    token_path=config.gcal_token_path,
    tz=config.tz,
)

SERVICE_LABELS = {
    "paddle_group": "🏓 Падел (групповая)",
    "paddle_ind": "🏓 Падел (индивидуальная)",
    "fitness": "🏋️ Фитнес",
}


async def show_available_times(message, state: FSMContext):
    data = await state.get_data()
    service = data["service"]
    date_str = data["date"]
    logger.debug(f"Showing available times for {service} on {date_str}")

    available = await repo.get_available_times(service, date_str)
    logger.info(f"Found {len(available)} available time slots for {service} on {date_str}: {available}")

    if not available:
        logger.warning(f"No available times for {service} on {date_str}")
        await message.edit_text(
            "😕 На выбранную дату мест уже нет. Выберите другую дату:",
            reply_markup=week_picker_kb(page=0, weeks_ahead=3)
        )
        return

    await state.set_state(BookingFlow.time)
    await message.edit_text(ASK_TIME, reply_markup=time_kb(available))
    logger.debug(f"Time selection keyboard displayed to user")


@router.message(F.text == "📅 Записаться на тренировку")
async def start_booking(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} started booking flow")
    await state.clear()
    await state.set_state(BookingFlow.service)
    await message.answer(ASK_SERVICE, reply_markup=services_kb())


@router.callback_query(BookingFlow.service, F.data.startswith("service:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    service = SERVICE_LABELS.get(key)
    logger.debug(f"User {call.from_user.id} selected service: {service}")
    if not service:
        logger.warning(f"Unknown service key: {key}")
        await call.answer("Не понял услугу. Выберите из списка.")
        return

    await state.update_data(service=service)
    await state.set_state(BookingFlow.date)

    await call.message.edit_text(ASK_DATE, reply_markup=date_kb())
    await call.answer()


@router.callback_query(BookingFlow.date, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    logger.debug(f"User {call.from_user.id} selected date option: {key}")

    if key == "today":
        d = date.today()
        date_str = d.strftime("%d.%m.%Y")
        logger.debug(f"Selected date: {date_str} (today)")
        await state.update_data(date=date_str)
        await show_available_times(call.message, state)
        await call.answer()
        return

    if key == "tomorrow":
        d = date.today() + timedelta(days=1)
        date_str = d.strftime("%d.%m.%Y")
        logger.debug(f"Selected date: {date_str} (tomorrow)")
        await state.update_data(date=date_str)
        await show_available_times(call.message, state)
        await call.answer()
        return

    if key == "pick":
        logger.debug("User requested calendar picker")
        await call.message.edit_text(
            "Выберите дату (можно пролистать недели):",
            reply_markup=week_picker_kb(page=0, weeks_ahead=3)
        )
        await call.answer()
        return

    if key == "back":
        logger.debug("User went back from date selection")
        await call.message.edit_text(ASK_DATE, reply_markup=date_kb())
        await call.answer()
        return

    logger.warning(f"Unknown date selection key: {key}")
    await call.answer("Неизвестный выбор даты.")


@router.callback_query(BookingFlow.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    t = call.data.split(":", 1)[1]
    logger.debug(f"User {call.from_user.id} selected time: {t}")

    # если у тебя в time_kb есть кнопка "назад к дате", делай ей отдельный callback:
    # if t == "back_date": ... (иначе это не будет ловиться)
    if t == "back_date":
        logger.debug("User went back to date selection")
        await state.set_state(BookingFlow.date)
        await call.message.edit_text(
            "Выберите дату (можно пролистать недели):",
            reply_markup=week_picker_kb(page=0, weeks_ahead=3),
        )
        await call.answer()
        return

    await state.update_data(time=t)
    await state.set_state(BookingFlow.name)

    await call.message.edit_text(ASK_NAME)
    await call.answer()


@router.message(BookingFlow.name)
async def get_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    logger.debug(f"User {message.from_user.id} entered name: {name}")
    if len(name) < 2:
        await message.answer("Слишком коротко. Напишите имя чуть понятнее 🙂")
        return

    await state.update_data(name=name)
    await state.set_state(BookingFlow.phone)
    await message.answer(ASK_PHONE)


@router.message(BookingFlow.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()
    logger.debug(f"User {message.from_user.id} entered phone: {phone}")

    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 7:
        logger.debug(f"Phone number too short (only {len(digits)} digits)")
        await message.answer("Похоже, номер слишком короткий. Введите телефон ещё раз:")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    logger.debug(f"User {message.from_user.id} ready for confirmation: {data}")

    await state.set_state(BookingFlow.confirm)
    await message.answer(
        CONFIRM_TEMPLATE.format(
            service=data["service"],
            date=data["date"],
            time=data["time"],
            name=data["name"],
            phone=data["phone"],
        ),
        reply_markup=confirm_kb()
    )


@router.callback_query(BookingFlow.confirm, F.data.startswith("confirm:"))
async def confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    choice = call.data.split(":", 1)[1]
    logger.debug(f"User {call.from_user.id} confirmed booking: {choice}")
    
    if choice == "no":
        logger.info(f"User {call.from_user.id} cancelled booking")
        await state.clear()
        await call.message.edit_text(CANCELLED)
        await call.answer()
        return

    data = await state.get_data()

    service = data["service"]
    date_str = data["date"]
    time_str = data["time"]
    name = data["name"]
    phone = data["phone"]
    user_id = str(call.from_user.id)

    logger.info(f"Creating booking for user {user_id}: {service} on {date_str} at {time_str}")

    # 1) создаём бронь в SQLite (источник правды) атомарно
    try:
        booking_id = await repo.create_booking(
            service=service,
            date=date_str,
            time=time_str,
            name=name,
            phone=phone,
            tg_user_id=user_id,
        )
    except SlotFullError:
        # слот заняли прямо сейчас
        logger.warning(f"Slot full for {service} on {date_str} at {time_str}")
        available = await repo.get_available_times(service, date_str)
        await state.set_state(BookingFlow.time)
        await call.message.edit_text(
            "⚠️ Упс! Это время только что заняли. Выберите другое:",
            reply_markup=time_kb(available)
        )
        await call.answer()
        return

    # 2) обновляем витрину Google Calendar (не должно ломать запись)
    try:
        logger.info(f"Updating Google Calendar for slot {service} on {date_str} at {time_str}")
        event_id = await publisher.upsert_slot_event(service, date_str, time_str)
        if event_id:
            await repo.attach_event_id_for_slot(service, date_str, time_str, event_id)
    except Exception as e:
        # бронь уже создана — календарь вторичен
        logger.error(f"Calendar update failed for slot {service} {date_str} {time_str}: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=config.admin_id,
                text=f"⚠️ Calendar update failed for slot {service} {date_str} {time_str}: {e}"
            )
        except Exception as notify_error:
            logger.error(f"Failed to notify admin about calendar update error: {notify_error}")

    # 3) клиенту
    logger.info(f"Booking {booking_id} confirmed for user {user_id}")
    await call.message.edit_text(BOOKED_USER)
    await call.answer()

    # 4) админу
    admin_text = (
        "📩 Новая запись (DEMO)\n\n"
        f"🆔 ID записи: {booking_id}\n"
        f"🏷 Услуга: {service}\n"
        f"📅 Дата: {date_str}\n"
        f"⏰ Время: {time_str}\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"👤 TG user_id: {user_id}"
    )
    try:
        await bot.send_message(chat_id=config.admin_id, text=admin_text)
        logger.info(f"Admin notified about booking {booking_id}")
    except Exception as e:
        logger.error(f"Failed to notify admin about booking {booking_id}: {e}")

    await state.clear()


@router.callback_query(BookingFlow.date, F.data.startswith("datepick:"))
async def pick_date_from_calendar(call: CallbackQuery, state: FSMContext):
    iso = call.data.split(":", 1)[1]  # YYYY-MM-DD
    y, m, d = iso.split("-")
    date_str = f"{d}.{m}.{y}"
    logger.debug(f"User {call.from_user.id} selected date from calendar: {date_str}")

    await state.update_data(date=date_str)
    await show_available_times(call.message, state)
    await call.answer()


@router.callback_query(BookingFlow.date, F.data.startswith("week:"))
async def switch_week(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":", 1)[1])
    logger.debug(f"User {call.from_user.id} switched to week page {page}")
    await call.message.edit_reply_markup(reply_markup=week_picker_kb(page=page, weeks_ahead=3))
    await call.answer()
