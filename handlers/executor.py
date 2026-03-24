from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import execute, fetchone, fetchall
from keyboards.inline import (
    task_card_executor, no_more_tasks, back_to_menu,
    get_menu_by_role, executor_work_menu, completion_keyboard
)
from states.task_states import ExecutorResponse
from utils.notifications import notify_user

router = Router()


# ══════════════════════════════════════════
# ЛЕНТА ЗАДАНИЙ
# ══════════════════════════════════════════

@router.callback_query(F.data == "browse_tasks")
async def browse_tasks(callback: CallbackQuery):
    # Показываем задания, на которые пользователь ещё НЕ откликался
    tasks = await fetchall(
        """SELECT t.* FROM tasks t
           WHERE t.status = 'approved'
           AND t.customer_id != ?
           AND t.task_id NOT IN (
               SELECT task_id FROM responses WHERE executor_id = ?
           )
           ORDER BY t.created_at DESC
           LIMIT 10""",
        (callback.from_user.id, callback.from_user.id)
    )

    if not tasks:
        return await callback.message.edit_text(
            "📭 Пока нет доступных заданий.\n\n"
            "Попробуйте позже!",
            reply_markup=no_more_tasks()
        )

    await callback.message.edit_text(
        f"🔍 Найдено заданий: {len(tasks)}\n"
        f"Листайте и откликайтесь!"
    )

    for task in tasks:
        text = (
            f"📌 **{task['title']}**\n\n"
            f"📄 {task['description']}\n\n"
            f"📂 Категория: {task['category']}\n"
            f"💰 Бюджет: {task['budget']:.0f}₽\n"
            f"📅 Срок: {task['deadline']}\n"
            f"📍 {task['location']}"
        )
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=task_card_executor(task["task_id"])
        )


# ══════════════════════════════════════════
# ОТКЛИК НА ЗАДАНИЕ
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("respond_"))
async def respond_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[1])

    # Проверяем повторный отклик
    existing = await fetchone(
        "SELECT * FROM responses WHERE task_id = ? AND executor_id = ?",
        (task_id, callback.from_user.id)
    )
    if existing:
        return await callback.answer("Вы уже откликнулись на это задание!", show_alert=True)

    await state.update_data(respond_task_id=task_id)
    await callback.message.answer(
        "✋ **Ваш отклик**\n\n"
        "Напишите сообщение заказчику:\n"
        "_Расскажите о своём опыте, задайте вопросы_",
        parse_mode="Markdown"
    )
    await state.set_state(ExecutorResponse.message)


@router.callback_query(F.data.startswith("skip_"))
async def skip_task(callback: CallbackQuery):
    await callback.message.delete()


@router.message(ExecutorResponse.message)
async def response_message(message: Message, state: FSMContext):
    if len(message.text) < 10:
        return await message.answer("❌ Напишите хотя бы 10 символов:")

    await state.update_data(response_message=message.text)

    data = await state.get_data()
    task = await fetchone(
        "SELECT budget FROM tasks WHERE task_id = ?",
        (data["respond_task_id"],)
    )

    await message.answer(
        f"💰 Укажите вашу цену за работу:\n\n"
        f"Бюджет заказчика: {task['budget']:.0f}₽\n"
        f"_Отправьте 0, чтобы согласиться с бюджетом_",
        parse_mode="Markdown"
    )
    await state.set_state(ExecutorResponse.proposed_price)


@router.message(ExecutorResponse.proposed_price)
async def response_price(message: Message, state: FSMContext, bot: Bot):
    try:
        price = float(message.text.replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError
    except ValueError:
        return await message.answer("❌ Введите корректное число:")

    data = await state.get_data()
    task_id = data["respond_task_id"]

    task = await fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    final_price = price if price > 0 else task["budget"]

    # Сохраняем отклик
    await execute(
        """INSERT INTO responses (task_id, executor_id, message, proposed_price, status)
           VALUES (?, ?, ?, ?, 'pending')""",
        (task_id, message.from_user.id, data["response_message"], final_price)
    )

    await state.clear()
    await message.answer(
        f"✅ **Отклик отправлен!**\n\n"
        f"📌 Задание: #{task_id}\n"
        f"💰 Ваша цена: {final_price:.0f}₽\n\n"
        f"Ожидайте решения заказчика.",
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )

    # Уведомляем заказчика
    user = await fetchone("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,))
    await notify_user(
        bot, task["customer_id"],
        f"🔔 **Новый отклик!**\n\n"
        f"Задание #{task_id}: {task['title']}\n\n"
        f"👤 {user['full_name']} (⭐ {user['rating']:.1f})\n"
        f"💬 {data['response_message']}\n"
        f"💰 Цена: {final_price:.0f}₽"
    )


# ══════════════════════════════════════════
# МОИ ОТКЛИКИ
# ══════════════════════════════════════════

@router.callback_query(F.data == "my_responses")
async def my_responses(callback: CallbackQuery):
    responses = await fetchall(
        """SELECT r.*, t.title, t.budget, t.status as task_status
           FROM responses r
           JOIN tasks t ON r.task_id = t.task_id
           WHERE r.executor_id = ?
           ORDER BY r.created_at DESC LIMIT 20""",
        (callback.from_user.id,)
    )

    if not responses:
        return await callback.message.edit_text(
            "📭 У вас пока нет откликов.",
            reply_markup=back_to_menu()
        )

    status_map = {
        "pending": "⏳ Ожидает",
        "accepted": "✅ Принят",
        "rejected": "❌ Отклонён",
    }

    text = "📋 **Ваши отклики:**\n\n"
    for resp in responses:
        status = status_map.get(resp["status"], resp["status"])
        text += (
            f"#{resp['task_id']} — {resp['title']}\n"
            f"   💰 {resp['proposed_price']:.0f}₽ | {status}\n\n"
        )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_to_menu()
    )


# ══════════════════════════════════════════
# АКТИВНЫЕ ЗАДАНИЯ (В РАБОТЕ)
# ══════════════════════════════════════════

@router.callback_query(F.data == "my_active_tasks")
async def my_active(callback: CallbackQuery):
    tasks = await fetchall(
        """SELECT * FROM tasks
           WHERE executor_id = ? AND status = 'in_progress'
           ORDER BY created_at DESC""",
        (callback.from_user.id,)
    )

    if not tasks:
        return await callback.message.edit_text(
            "📭 Нет активных заданий.",
            reply_markup=back_to_menu()
        )

    for task in tasks:
        text = (
            f"🔨 **Задание #{task['task_id']}**\n\n"
            f"📌 {task['title']}\n"
            f"📄 {task['description']}\n"
            f"💰 {task['budget']:.0f}₽\n"
            f"📅 {task['deadline']}\n"
            f"📍 {task['location']}"
        )
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=executor_work_menu(task["task_id"])
        )


# ══════════════════════════════════════════
# ОТМЕТИТЬ ВЫПОЛНЕНИЕ
# ══════════════════════════════════════════

@router.callback_query(F.data.startswith("done_"))
async def mark_done(callback: CallbackQuery, bot: Bot):
    task_id = int(callback.data.split("_")[1])

    task = await fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not task:
        return await callback.answer("Не найдено")

    await execute(
        "UPDATE tasks SET status = 'done_pending' WHERE task_id = ?",
        (task_id,)
    )

    await callback.message.edit_text(
        f"📤 Задание #{task_id} отмечено как выполненное!\n\n"
        f"Ожидайте подтверждения заказчика.",
        reply_markup=back_to_menu()
    )

    await notify_user(
        bot, task["customer_id"],
        f"🔔 **Исполнитель завершил работу!**\n\n"
        f"Задание #{task_id}: **{task['title']}**\n\n"
        f"Проверьте и подтвердите выполнение:",
        reply_markup=completion_keyboard(task_id)
    )