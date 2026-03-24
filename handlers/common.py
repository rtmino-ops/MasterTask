from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.db import execute, fetchone
from keyboards.inline import role_selection, get_menu_by_role, back_to_menu
from states.task_states import Registration
from config import ADMIN_IDS

router = Router()


# ══════════════════════════════════════════
# /start
# ══════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (message.from_user.id,)
    )

    if user:
        role = user["role"]
        await message.answer(
            f"👋 С возвращением, **{message.from_user.full_name}**!\n\n"
            f"Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_menu_by_role(role)
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в **TaskBot**!\n\n"
            "🔹 Заказчики размещают задания\n"
            "🔹 Исполнители берутся за работу\n"
            "🔹 Деньги защищены до подтверждения\n\n"
            "Выберите свою роль:",
            parse_mode="Markdown",
            reply_markup=role_selection()
        )


# ══════════════════════════════════════════
# РЕГИСТРАЦИЯ
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    role_map = {
        "role_customer": "customer",
        "role_executor": "executor",
        "role_both": "both",
    }
    role = role_map.get(callback.data, "customer")

    role_names = {
        "customer": "👔 Заказчик",
        "executor": "🔧 Исполнитель",
        "both": "🔄 Заказчик + Исполнитель",
    }

    # Проверяем — может уже есть
    existing = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (callback.from_user.id,)
    )

    if existing:
        await execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, callback.from_user.id)
        )
    else:
        await execute(
            """INSERT INTO users (user_id, username, full_name, role)
               VALUES (?, ?, ?, ?)""",
            (
                callback.from_user.id,
                callback.from_user.username or "",
                callback.from_user.full_name or "Пользователь",
                role,
            )
        )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Регистрация завершена!\n\n"
        f"Ваша роль: {role_names[role]}\n\n"
        f"Выберите действие:",
        reply_markup=get_menu_by_role(role)
    )


# ══════════════════════════════════════════
# ГЛАВНОЕ МЕНЮ
# ══════════════════════════════════════════

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (callback.from_user.id,)
    )
    if not user:
        return await callback.message.edit_text(
            "Нажмите /start для регистрации"
        )

    await callback.message.edit_text(
        "🏠 **Главное меню**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_menu_by_role(user["role"])
    )


# ══════════════════════════════════════════
# ПРОФИЛЬ
# ══════════════════════════════════════════

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (callback.from_user.id,)
    )
    if not user:
        return await callback.answer("Профиль не найден")

    role_names = {
        "customer": "👔 Заказчик",
        "executor": "🔧 Исполнитель",
        "both": "🔄 Заказчик + Исполнитель",
    }

    # Считаем статистику
    tasks_created = await fetchone(
        "SELECT COUNT(*) as c FROM tasks WHERE customer_id = ?",
        (callback.from_user.id,)
    )
    tasks_done = await fetchone(
        "SELECT COUNT(*) as c FROM tasks WHERE executor_id = ? AND status = 'completed'",
        (callback.from_user.id,)
    )

    text = (
        f"👤 **Ваш профиль**\n\n"
        f"📛 Имя: {user['full_name']}\n"
        f"🆔 Username: @{user['username']}\n"
        f"🎭 Роль: {role_names.get(user['role'], user['role'])}\n"
        f"⭐ Рейтинг: {user['rating']:.1f} "
        f"({user['reviews_count']} отзывов)\n"
        f"📝 Создано заданий: {tasks_created['c']}\n"
        f"✅ Выполнено: {tasks_done['c']}\n"
        f"💰 Баланс: {user['balance']:.2f}₽\n"
        f"📅 Зарегистрирован: {user['registered_at']}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )


# ══════════════════════════════════════════
# БАЛАНС
# ══════════════════════════════════════════

@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (callback.from_user.id,)
    )
    if not user:
        return await callback.answer("Ошибка")

    # Считаем удержанные деньги
    held = await fetchone(
        """SELECT COALESCE(SUM(amount), 0) as total
           FROM transactions
           WHERE (from_user = ? OR to_user = ?)
           AND status = 'held'""",
        (callback.from_user.id, callback.from_user.id)
    )

    text = (
        f"💰 **Ваш баланс**\n\n"
        f"Доступно: {user['balance']:.2f}₽\n"
        f"На удержании: {held['total']:.2f}₽\n\n"
        f"_Вывод средств будет доступен\n"
        f"после подключения платёжной системы_"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )


# ══════════════════════════════════════════
# КОМАНДА /help
# ══════════════════════════════════════════

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 **Как это работает:**\n\n"
        "1️⃣ Заказчик создаёт задание\n"
        "2️⃣ Модератор проверяет и одобряет\n"
        "3️⃣ Исполнители видят задание и откликаются\n"
        "4️⃣ Заказчик выбирает исполнителя\n"
        "5️⃣ Заказчик оплачивает (деньги на эскроу)\n"
        "6️⃣ Исполнитель выполняет работу\n"
        "7️⃣ Заказчик подтверждает → деньги исполнителю\n\n"
        "**Команды:**\n"
        "/start — Главное меню\n"
        "/help — Эта справка\n"
        "/profile — Ваш профиль\n"
    )
    is_admin = message.from_user.id in ADMIN_IDS
    if is_admin:
        text += "/admin — Панель администратора\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await fetchone(
        "SELECT * FROM users WHERE user_id = ?",
        (message.from_user.id,)
    )
    if not user:
        return await message.answer("Нажмите /start для регистрации")

    await message.answer(
        "👤 Ваш профиль:",
        reply_markup=back_to_menu()
    )