from aiogram.fsm.state import StatesGroup, State


class BookingFlow(StatesGroup):
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()
