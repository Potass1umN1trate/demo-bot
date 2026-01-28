from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import logging

from app.states import AdminFlow
from app.keyboards import admin_main_kb, admin_manage_kb, cancel_kb
from app.config import load_config
from app.repo import Repo

logger = logging.getLogger(__name__)

router = Router()

# Load config and repo at module level (singleton pattern)
config = load_config()
repo = Repo(config.db_path)


async def check_admin_access(user_id: int, is_owner_only: bool = False) -> bool:
    """Check if user has admin access"""
    user_id_str = str(user_id)
    if is_owner_only:
        return await repo.is_owner(user_id_str)
    return await repo.is_admin(user_id_str)


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    logger.info(f"User {user_id} accessed /admin command")
    
    # Check if admin
    if not await check_admin_access(user_id):
        logger.warning(f"User {user_id} tried to access admin panel without permissions")
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    is_owner = await check_admin_access(user_id, is_owner_only=True)
    logger.debug(f"User {user_id} is_owner: {is_owner}")
    
    await state.set_state(AdminFlow.main_menu)
    await message.answer(
        "🔧 Админ-панель\n\nВыберите действие:",
        reply_markup=admin_main_kb(is_owner=is_owner)
    )


@router.callback_query(AdminFlow.main_menu, F.data == "manage_bookings")
async def manage_bookings_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    
    if not await check_admin_access(user_id):
        await call.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    logger.info(f"User {user_id} opened bookings management")
    await state.set_state(AdminFlow.manage_bookings)
    
    bookings = await repo.get_all_bookings(limit=50)
    text = f"📋 Всего записей: {len(bookings)}\n\n"
    
    for b in bookings[:10]:  # Show first 10
        status_emoji = "✅" if b.status == "active" else "❌"
        text += f"{status_emoji} ID {b.id}: {b.name} ({b.phone})\n"
        text += f"  {b.service} {b.date} {b.time}\n\n"
    
    if len(bookings) > 10:
        text += f"... и еще {len(bookings) - 10} записей"
    
    await call.message.edit_text(text, reply_markup=cancel_kb())
    await call.answer()


@router.callback_query(AdminFlow.main_menu, F.data == "manage_services")
async def manage_services_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    
    if not await check_admin_access(user_id):
        await call.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    logger.info(f"User {user_id} opened services management")
    await state.set_state(AdminFlow.manage_services)
    
    services = await repo.get_all_services()
    text = "⚙️ Услуги:\n\n"
    
    for service_id, name, capacity, enabled in services:
        status = "✅" if enabled else "❌"
        text += f"{status} {name} (вместимость: {capacity})\n"
    
    if not services:
        text += "Услуги не добавлены"
    
    await call.message.edit_text(text, reply_markup=cancel_kb())
    await call.answer()


@router.callback_query(AdminFlow.main_menu, F.data == "manage_admins")
async def manage_admins_menu(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    
    if not await check_admin_access(user_id, is_owner_only=True):
        logger.warning(f"User {user_id} tried to access admin management without owner permissions")
        await call.answer("❌ Только владелец может управлять админами", show_alert=True)
        return
    
    logger.info(f"User {user_id} (owner) opened admins management")
    await state.set_state(AdminFlow.manage_admins)
    
    admins = await repo.get_all_admins()
    text = "👥 Администраторы:\n\n"
    
    for tg_user_id, username, is_owner in admins:
        role = "👑 Владелец" if is_owner else "🔑 Админ"
        username_str = f"@{username}" if username else f"ID: {tg_user_id}"
        text += f"{role} - {username_str}\n"
    
    if not admins:
        text += "Администраторы не добавлены"
    
    await call.message.edit_text(text, reply_markup=cancel_kb())
    await call.answer()


@router.callback_query(F.data == "cancel")
async def cancel_admin_action(call: CallbackQuery, state: FSMContext):
    logger.debug(f"User {call.from_user.id} cancelled admin action")
    await state.clear()
    await call.message.edit_text("❌ Отменено")
    await call.answer()
