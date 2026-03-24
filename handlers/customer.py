from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import execute, fetchone, fetchall
from keyboards.inline import (
    task_categories, task_confirm, back_to_menu,
    get_menu_by_role, task_actions_customer,
    response_card, payment_keyboard,
    completion_keyboard, review_stars
)
from states.task_states import CreateTask, DisputeState, ReviewState
from utils.notifications import notify_user, notify_admins
from config import ADMIN_IDS, SERVICE_FEE
from keyboards.inline import admin_task_review

router = Router()


# ══════════════════════════════════════════
# СОЗДАНИЕ ЗАДАНИЯ
# ══════════════════════════════════════════

@router.callback_query(F.data == "create_task")
async def start_create(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📝 **Создание задания** (шаг 1/5)\n\n"
        "Введите название задания:\n\n"
        "_Например: Собрать шкаф IKEA_",
        parse_mode="Markdown"
    )
    await state.set_state(CreateTask.title)


@router.callback_query(F.data == "cancel_create")
async def cancel_create(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await fetchone("SELECT role FROM users WHERE user_id = ?", (callback.from_user.id,))
    await callback.message.edit_text(
        "❌ Создание отменено.",
        reply_markup=get_menu_by_role(user["role"] if user else "customer")
    )


@router.message(CreateTask.title)
async def process_title(message: Message, state: FSMContext):
    if len(message.text) < 5:
        return await message.answer("❌ Слишком короткое название. Минимум 5 символов:")
    if len(message.text) > 100:
        return await message.answer("❌ Слишком длинное. Максимум 100 символов:")

    await state.update_data(title=message.text)
    await message.answer(
        "📝 **Шаг 2/5**\n\n"
        "Опишите подробно, что нужно сделать:\n\n"
        "_Чем подробнее — тем точнее будут отклики_",
        parse_mode="Markdown"
    )
    await state.set_state(CreateTask.description)


@router.message(CreateTask.description)
async def process_description(message: Message, state: FSMContext):
    if len(message.text) < 10:
        return await message.answer("❌ Слишком короткое описание. Минимум 10 символов:")

    await state.update_data(description=message.text)
    await message.answer(
        "📝 **Шаг 3/5**\n\n"
        "Выберите категорию:",
        parse_mode="Markdown",
        reply_markup=task_categories()
    )
    await state.set_state(CreateTask.category)


@router.callback_query(CreateTask.category, F.data.startswith("cat_"))
async def process_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await callback.message.edit_text(
        "📝 **Шаг 4/5**\n\n"
        "💰 Укажите бюджет в рублях:\n\n"
        "_Например: 5000_",
        parse_mode="Markdown"
    )
    await state.set_state(CreateTask.budget)


@router.message(CreateTask.budget)
async def process_budget(message: Message, state: FSMContext):
    try:
        budget = float(message.text.replace(",", ".").replace(" ", ""))
        if budget < 100:
            return await message.answer("❌ Минимальный бюджет — 100₽:")
        if budget > 1000000:
            return await message.answer("❌ Максимальный бюджет — 1 000 000₽:")
    except ValueError:
        return await message.answer("❌ Введите число:")

    await state.update_data(budget=budget)
    await message.answer(
        "📝 **Шаг 5/5**\n\n"
        "📅 Укажите срок выполнения:\n\n"
        "_Например: до 25 июля / 3 дня / без срока_",
        parse_mode="Markdown"
    )
    await state.set_state(CreateTask.deadline)


@router.message(CreateTask.deadline)
async def process_deadline(message: Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    await message.answer(
        "📍 Где нужно выполнить задание?\n\n"
        "_Например: Москва, ул. Ленина 5 / Удалённо_",
        parse_mode="Markdown"
    )
    await state.set_state(CreateTask.location)


@router.message(CreateTask.location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    data = await state.get_data()

    preview = (
        f"📋 **Предпросмотр задания:**\n\n"
        f"📌 **{data['title']}**\n\n"
        f"📄 {data['description']}\n\n"
        f"📂 Категория: {data['category']}\n"
        f"💰 Бюджет: {data['budget']:.0f}₽\n"
        f"📅 Срок: {data['deadline']}\n"
        f"📍 Место: {data['location']}\n\n"
        f"Всё верно?"
    )
    await message.answer(
        preview,
        parse_mode="Markdown",
        reply_markup=task_confirm()
    )
    await state.set_state(CreateTask.confirm)


@router.callback_query(CreateTask.confirm, F.data == "confirm_task")
async def confirm_task(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    task_id = await execute(
        """INSERT INTO tasks
           (customer_id, title, description, category, budget, deadline, location, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_review')""",
        (
            callback.from_user.id,
            data["title"], data["description"], data["category"],
            data["budget"], data["deadline"], data["location"],
        )
    )

    await state.clear()
    await callback.message.edit_text(
        f"✅ Задание **#{task_id}** отправлено на модерацию!\n\n"
        f"Вы получите уведомление после проверки.",
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )

    # Уведомляем админов
    admin_text = (
        f"🆕 **Новое задание #{task_id} на модерации**\n\n"
        f"📌 {data['title']}\n"
        f"📄 {data['description']}\n"
        f"📂 {data['category']}\n"
        f"💰 {data['budget']:.0f}₽\n"
        f"📅 {data['deadline']}\n"
        f"📍 {data['location']}\n"
        f"👤 {callback.from_user.full_name} (@{callback.from_user.username})"
    )
    await notify_admins(bot, ADMIN_IDS, admin_text, admin_task_review(task_id))


@router.callback_query(CreateTask.confirm, F.data == "edit_task")
async def edit_task(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "✏️ Давайте начнём заново.\n\n"
        "Введите название задания:",
    )
    await state.set_state(CreateTask.title)


# ══════════════════════════════════════════
# МОИ ЗАДАНИЯ
# ══════════════════════════════════════════

@router.callback_query(F.data == "my_tasks_customer")
async def my_tasks(callback: CallbackQuery):
    tasks = await fetchall(
        """SELECT * FROM tasks
           WHERE customer_id = ?
           ORDER BY created_at DESC LIMIT 20""",
        (callback.from_user.id,)
    )

    if not tasks:
        return await callback.message.edit_text(
            "📭 У вас пока нет заданий.\n\n"
            "Нажмите «Создать задание» в меню!",
            reply_markup=back_to_menu()
        )

    status_map = {
        "pending_review": "🔍 На модерации",
        "approved": "✅ Ищет исполнителя",
        "in_progress": "🔨 В работе",
        "done_pending": "📤 Ожидает подтверждения",
        "completed": "🏁 Завершено",
        "disputed": "⚠️ Спор",
        "rejected": "❌ Отклонено",
        "cancelled": "🚫 Отменено",
    }

    text = "📋 **Ваши задания:**\n\n"
    for task in tasks:
        status = status_map.get(task["status"], task["status"])
        text += f"#{task['task_id']} — {task['title']}\n"
        text += f"   💰 {task['budget']:.0f}₽ | {status}\n\n"

    # Кнопки для каждого задания
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for task in tasks:
        if task["status"] in ("approved", "in_progress", "done_pending"):
            builder.row(InlineKeyboardButton(
                text=f"📌 #{task['task_id']} {task['title'][:20]}",
                callback_data=f"task_detail_{task['task_id']}"
            ))
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("task_detail_"))
async def task_detail(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])

    task = await fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        return await callback.answer("Задание не найдено")

    # Считаем отклики
    resp_count = await fetchone(
        "SELECT COUNT(*) as c FROM responses WHERE task_id = ?",
        (task_id,)
    )

    executor_info = ""
    if task["executor_id"]:
        executor = await fetchone(
            "SELECT * FROM users WHERE user_id = ?",
            (task["executor_id"],)
        )
        if executor:
            executor_info = (
                f"\n👷 Исполнитель: {executor['full_name']} "
                f"(@{executor['username']})\n"
                f"⭐ Рейтинг: {executor['rating']:.1f}\n"
            )

    text = (
        f"📋 **Задание #{task_id}**\n\n"
        f"📌 {task['title']}\n"
        f"📄 {task['description']}\n\n"
        f"💰 Бюджет: {task['budget']:.0f}₽\n"
        f"📅 Срок: {task['deadline']}\n"
        f"📍 Место: {task['location']}\n"
        f"📊 Статус: {task['status']}\n"
        f"👥 Откликов: {resp_count['c']}"
        f"{executor_info}"
    )

    has_responses = resp_count["c"] > 0
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=task_actions_customer(task_id, has_responses)
    )


# ══════════════════════════════════════════
# ПРОСМОТР ОТКЛИКОВ
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("view_responses_"))
async def view_responses(callback: CallbackQuery):
    task_id = int(callback.data.split("_")[2])

    responses = await fetchall(
        """SELECT r.*, u.full_name, u.username, u.rating, u.tasks_completed
           FROM responses r
           JOIN users u ON r.executor_id = u.user_id
           WHERE r.task_id = ? AND r.status = 'pending'
           ORDER BY r.created_at ASC""",
        (task_id,)
    )

    if not responses:
        return await callback.message.edit_text(
            "📭 Пока нет откликов на это задание.",
            reply_markup=back_to_menu()
        )

    for resp in responses:
        text = (
            f"👤 **{resp['full_name']}** (@{resp['username']})\n"
            f"⭐ Рейтинг: {resp['rating']:.1f} | "
            f"✅ Выполнено: {resp['tasks_completed']}\n\n"
            f"💬 {resp['message']}\n"
            f"💰 Предложенная цена: {resp['proposed_price']:.0f}₽"
        )
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=response_card(resp["response_id"], task_id)
        )


# ══════════════════════════════════════════
# ВЫБОР ИСПОЛНИТЕЛЯ → ОПЛАТА
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("pick_"))
async def pick_executor(callback: CallbackQuery, bot: Bot):
    response_id = int(callback.data.split("_")[1])

    resp = await fetchone(
        """SELECT r.*, u.full_name, t.budget, t.task_id, t.title
           FROM responses r
           JOIN users u ON r.executor_id = u.user_id
           JOIN tasks t ON r.task_id = t.task_id
           WHERE r.response_id = ?""",
        (response_id,)
    )

    if not resp:
        return await callback.answer("Отклик не найден")

    price = resp["proposed_price"]
    fee = price * SERVICE_FEE / 100
    total = price + fee

    # Запоминаем исполнителя
    await execute(
        "UPDATE tasks SET executor_id = ? WHERE task_id = ?",
        (resp["executor_id"], resp["task_id"])
    )
    await execute(
        "UPDATE responses SET status = 'accepted' WHERE response_id = ?",
        (response_id,)
    )

    await callback.message.edit_text(
        f"🤝 **Вы выбрали исполнителя!**\n\n"
        f"👤 {resp['full_name']}\n"
        f"📌 Задание: {resp['title']}\n\n"
        f"💰 Цена работы: {price:.0f}₽\n"
        f"📊 Комиссия сервиса ({SERVICE_FEE}%): {fee:.0f}₽\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💳 **Итого: {total:.0f}₽**\n\n"
        f"Оплатите, чтобы закрепить исполнителя.\n"
        f"Деньги будут на эскроу до подтверждения.",
        parse_mode="Markdown",
        reply_markup=payment_keyboard(resp["task_id"], total)
    )


@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, bot: Bot):
    task_id = int(callback.data.split("_")[1])

    task = await fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task or not task["executor_id"]:
        return await callback.answer("Ошибка")

    # Рассчитываем сумму
    resp = await fetchone(
        "SELECT proposed_price FROM responses WHERE task_id = ? AND status = 'accepted'",
        (task_id,)
    )
    price = resp["proposed_price"] if resp else task["budget"]

    # === ЗАГЛУШКА ОПЛАТЫ ===
    # В будущем здесь будет реальная платёжка
    await execute(
        """INSERT INTO transactions (task_id, from_user, to_user, amount, tx_type, status)
           VALUES (?, ?, ?, ?, 'escrow', 'held')""",
        (task_id, task["customer_id"], task["executor_id"], price)
    )

    await execute(
        "UPDATE tasks SET status = 'in_progress' WHERE task_id = ?",
        (task_id,)
    )

    await callback.message.edit_text(
        f"✅ **Оплата принята!**\n\n"
        f"Задание #{task_id} теперь в работе.\n"
        f"💰 {price:.0f}₽ удержаны до подтверждения выполнения.\n\n"
        f"Исполнитель получил уведомление.",
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )

    # Уведомляем исполнителя
    from keyboards.inline import executor_work_menu
    await notify_user(
        bot, task["executor_id"],
        f"🎉 **Вас выбрали!**\n\n"
        f"Задание #{task_id}: **{task['title']}**\n"
        f"💰 Оплата: {price:.0f}₽\n\n"
        f"Заказчик оплатил. Приступайте к работе!",
        reply_markup=executor_work_menu(task_id)
    )


# ══════════════════════════════════════════
# ПОДТВЕРЖДЕНИЕ / СПОР
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("complete_"))
async def confirm_completion(callback: CallbackQuery, state: FSMContext, bot: Bot):
    task_id = int(callback.data.split("_")[1])

    task = await fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        return await callback.answer("Не найдено")

    # Получаем сумму из транзакции
    tx = await fetchone(
        "SELECT amount FROM transactions WHERE task_id = ? AND status = 'held'",
        (task_id,)
    )
    amount = tx["amount"] if tx else task["budget"]
    fee = amount * SERVICE_FEE / 100
    payout = amount - fee

    # Переводим деньги
    await execute(
        "UPDATE transactions SET status = 'released' WHERE task_id = ? AND status = 'held'",
        (task_id,)
    )
    await execute(
        "UPDATE tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE task_id = ?",
        (task_id,)
    )
    await execute(
        """UPDATE users SET balance = balance + ?, tasks_completed = tasks_completed + 1
           WHERE user_id = ?""",
        (payout, task["executor_id"])
    )

    # Предлагаем оставить отзыв
    await state.update_data(review_task_id=task_id, review_to=task["executor_id"])
    await state.set_state(ReviewState.rating)

    await callback.message.edit_text(
        f"🏁 **Задание #{task_id} завершено!**\n\n"
        f"💰 {payout:.0f}₽ переведено исполнителю\n"
        f"📊 Комиссия сервиса: {fee:.0f}₽\n\n"
        f"Оцените работу исполнителя:",
        parse_mode="Markdown",
        reply_markup=review_stars()
    )

    await notify_user(
        bot, task["executor_id"],
        f"✅ Задание #{task_id} подтверждено!\n"
        f"💰 {payout:.0f}₽ зачислено на баланс."
    )


# ══════════════════════════════════════════
# ОТЗЫВ
# ══════════════════════════════════════════

@router.callback_query(ReviewState.rating, F.data.startswith("stars_"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await callback.message.edit_text(
        f"⭐ Оценка: {'⭐' * rating}\n\n"
        f"Напишите комментарий (или отправьте «-» чтобы пропустить):"
    )
    await state.set_state(ReviewState.comment)


@router.message(ReviewState.comment)
async def process_review_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text if message.text != "-" else ""

    await execute(
        """INSERT INTO reviews (task_id, from_user, to_user, rating, comment)
           VALUES (?, ?, ?, ?, ?)""",
        (data["review_task_id"], message.from_user.id, data["review_to"], data["rating"], comment)
    )

    # Обновляем средний рейтинг
    avg = await fetchone(
        "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM reviews WHERE to_user = ?",
        (data["review_to"],)
    )
    await execute(
        "UPDATE users SET rating = ?, reviews_count = ? WHERE user_id = ?",
        (avg["avg_r"], avg["cnt"], data["review_to"])
    )

    await state.clear()
    user = await fetchone("SELECT role FROM users WHERE user_id = ?", (message.from_user.id,))
    await message.answer(
        f"✅ Спасибо за отзыв!",
        reply_markup=get_menu_by_role(user["role"] if user else "customer")
    )


# ══════════════════════════════════════════
# СПОР
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("dispute_"))
async def open_dispute(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])
    await state.update_data(dispute_task_id=task_id)
    await callback.message.edit_text(
        "⚠️ **Открытие спора**\n\n"
        "Деньги будут удержаны до решения.\n\n"
        "Опишите причину спора:",
        parse_mode="Markdown"
    )
    await state.set_state(DisputeState.reason)


@router.message(DisputeState.reason)
async def process_dispute(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data["dispute_task_id"]

    await execute(
        """INSERT INTO disputes (task_id, opened_by, reason, status)
           VALUES (?, ?, ?, 'open')""",
        (task_id, message.from_user.id, message.text)
    )
    await execute(
        "UPDATE tasks SET status = 'disputed' WHERE task_id = ?",
        (task_id,)
    )

    await state.clear()
    await message.answer(
        f"⚠️ Спор по заданию #{task_id} открыт.\n\n"
        f"💰 Деньги удержаны до решения.\n"
        f"Поддержка рассмотрит вашу заявку.",
        reply_markup=back_to_menu()
    )

    await notify_admins(
        bot, ADMIN_IDS,
        f"⚠️ **Новый спор!**\n\n"
        f"Задание: #{task_id}\n"
        f"Открыл: @{message.from_user.username}\n"
        f"Причина: {message.text}"
    )