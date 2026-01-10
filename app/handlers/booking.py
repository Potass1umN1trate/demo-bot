from datetime import date, timedelta

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
from app.db import insert_booking, count_bookings_for_slot

router = Router()
config = load_config()  # для демо нормально: один конфиг на процесс


SERVICE_LABELS = {
    "paddle_group": "🏓 Падел (групповая)",
    "paddle_ind": "🏓 Падел (индивидуальная)",
    "fitness": "🏋️ Фитнес",
}

CAPACITY = {
    "🏓 Падел (групповая)": 3,
    "🏓 Падел (индивидуальная)": 1,
    "🏋️ Фитнес": 10,
}

TIME_SLOTS = [f"{h:02d}:00" for h in range(10, 23)]  # 10..22 включительно

async def show_available_times(message, state: FSMContext):
    data = await state.get_data()
    service = data["service"]
    date_str = data["date"]

    cap = CAPACITY.get(service, 1)

    available = []
    for t in TIME_SLOTS:
        used = count_bookings_for_slot(config.db_path, service, date_str, t)
        if used < cap:
            available.append(t)

    if not available:
        await message.edit_text(
            "😕 На выбранную дату мест уже нет. Выберите другую дату:",
            reply_markup=week_picker_kb(page=0, weeks_ahead=3)  # если ты уже внедрил недельный календарь
        )
        return

    await state.set_state(BookingFlow.time)
    await message.edit_text(ASK_TIME, reply_markup=time_kb(available))


@router.message(F.text == "📅 Записаться на тренировку")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BookingFlow.service)
    await message.answer(ASK_SERVICE, reply_markup=services_kb())


@router.callback_query(BookingFlow.service, F.data.startswith("service:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    service = SERVICE_LABELS.get(key)
    if not service:
        await call.answer("Не понял услугу. Выберите из списка.")
        return

    await state.update_data(service=service)
    await state.set_state(BookingFlow.date)

    await call.message.edit_text(ASK_DATE, reply_markup=date_kb())
    await call.answer()


@router.callback_query(BookingFlow.date, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]

    if key == "today":
        d = date.today()
        date_str = d.strftime("%d.%m.%Y")
        await state.update_data(date=date_str)
        await show_available_times(call.message, state)
        await call.answer()
        return

    if key == "tomorrow":
        d = date.today() + timedelta(days=1)
        date_str = d.strftime("%d.%m.%Y")
        await state.update_data(date=date_str)
        await show_available_times(call.message, state)
        await call.answer()
        return

    if key == "pick":
        await call.message.edit_text(
            "Выберите дату (можно пролистать недели):",
            reply_markup=week_picker_kb(page=0, weeks_ahead=3)
        )
        await call.answer()
        return

    if key == "back":
        await call.message.edit_text(ASK_DATE, reply_markup=date_kb())
        await call.answer()
        return



    await call.answer("Неизвестный выбор даты.")

@router.callback_query(BookingFlow.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    t = call.data.split(":", 1)[1]
    await state.update_data(time=t)
    await state.set_state(BookingFlow.name)

    await call.message.edit_text(ASK_NAME)
    await call.answer()


@router.message(BookingFlow.name)
async def get_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Слишком коротко. Напишите имя чуть понятнее 🙂")
        return

    await state.update_data(name=name)
    await state.set_state(BookingFlow.phone)
    await message.answer(ASK_PHONE)


@router.message(BookingFlow.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()

    # Мини-валидация: хотя бы 7 цифр
    digits = [c for c in phone if c.isdigit()]
    if len(digits) < 7:
        await message.answer("Похоже, номер слишком короткий. Введите телефон ещё раз:")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()

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
    if choice == "no":
        await state.clear()
        await call.message.edit_text(CANCELLED)
        await call.answer()
        return

    data = await state.get_data()

    booking = {
        "user_id": call.from_user.id,
        "service": data["service"],
        "date": data["date"],
        "time": data["time"],
        "name": data["name"],
        "phone": data["phone"],
    }

    cap = CAPACITY.get(booking["service"], 1)
    used = count_bookings_for_slot(config.db_path, booking["service"], booking["date"], booking["time"])
    if used >= cap:
        # слот уже заняли
        await call.message.edit_text(
            "⚠️ Упс! Это время только что заняли. Выберите другое:",
            reply_markup=time_kb([
                t for t in TIME_SLOTS
                if count_bookings_for_slot(config.db_path, booking["service"], booking["date"], t) < cap
            ])
        )
        await state.set_state(BookingFlow.time)
        await call.answer()
        return

    row_id = insert_booking(config.db_path, booking)

    # 1) клиенту
    await call.message.edit_text(BOOKED_USER)
    await call.answer()

    # 2) админу
    admin_text = (
        "📩 Новая запись (DEMO)\n\n"
        f"🆔 ID записи: {row_id}\n"
        f"🏷 Услуга: {booking['service']}\n"
        f"📅 Дата: {booking['date']}\n"
        f"⏰ Время: {booking['time']}\n"
        f"👤 Имя: {booking['name']}\n"
        f"📞 Телефон: {booking['phone']}\n"
        f"👤 TG user_id: {booking['user_id']}"
    )
    await bot.send_message(chat_id=config.admin_id, text=admin_text)

    await state.clear()

@router.callback_query(BookingFlow.date, F.data.startswith("datepick:"))
async def pick_date_from_calendar(call: CallbackQuery, state: FSMContext):
    iso = call.data.split(":", 1)[1]  # YYYY-MM-DD
    y, m, d = iso.split("-")
    date_str = f"{d}.{m}.{y}"

    await state.update_data(date=date_str)
    await show_available_times(call.message, state)
    await call.answer()

@router.callback_query(BookingFlow.date, F.data.startswith("week:"))
async def switch_week(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":", 1)[1])
    await call.message.edit_reply_markup(reply_markup=week_picker_kb(page=page, weeks_ahead=3))
    await call.answer()
