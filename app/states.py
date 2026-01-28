from aiogram.fsm.state import StatesGroup, State


class BookingFlow(StatesGroup):
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


class AdminFlow(StatesGroup):
    main_menu = State()
    # Bookings
    manage_bookings = State()
    view_bookings = State()
    edit_booking = State()
    delete_booking = State()
    add_booking = State()
    # Services
    manage_services = State()
    view_services = State()
    edit_service = State()
    delete_service = State()
    add_service = State()
    # Admins (owner only)
    manage_admins = State()
    add_admin = State()
    delete_admin = State()

