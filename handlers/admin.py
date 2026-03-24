from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.db import execute, fetchone, fetchall
from keyboards.inline import admin_menu, admin_task_review, dispute_resolution
from utils.notifications import notify_user
from config import ADMIN_IDS

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа")
    pending = await fetchone(
        "SELECT COUNT(*) as c FROM tasks WHERE status = 'pending_review'"
    )
    active = await fetchone(
        "SELECT COUNT(*) as c FROM tasks WHERE status = 'in_progress'"
    )
    disputes = await fetchone(
        "SELECT COUNT(*) as c FROM disputes WHERE status = 'open'"
    )
    users = await fetchone("SELECT COUNT(*) as c FROM users")
    text = (
        "Админ-панел��\n\n"
        f"Пользователей: {users['c']}\n"
        f"На модерации: {pending['c']}\n"
        f"В работе: {active['c']}\n"
        f"Споров: {disputes['c']}"
    )
    await message.answer(text, reply_markup=admin_menu())


@router.callback_query(F.data == "admin_pending")
async def admin_pending(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    tasks = await fetchall(
        "SELECT t.*, u.full_name, u.username FROM tasks t "
        "JOIN users u ON t.customer_id = u.user_id "
        "WHERE t.status = 'pending_review' "
        "ORDER BY t.created_at ASC"
    )
    if not tasks:
        return await callback.message.edit_text(
            "Нет заданий на модерации!",
            reply_markup=admin_menu()
        )
    for task in tasks:
        username = task['username'] or 'нет'
        text = (
            f"Модерация задания #{task['task_id']}\n\n"
            f"Название: {task['title']}\n"
            f"Описание: {task['description']}\n"
            f"Бюджет: {task['budget']:.0f} руб\n"
            f"Категория: {task['category']}\n"
            f"Срок: {task['deadline']}\n"
            f"Место: {task['location']}\n"
            f"От: {task['full_name']} (tg: {username})"
        )
        await callback.message.answer(
            text,
            reply_markup=admin_task_review(task["task_id"])
        )


@router.callback_query(F.data.startswith("approve_"))
async def approve_task(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return
    task_id = int(callback.data.split("_")[1])
    await execute(
        "UPDATE tasks SET status = 'approved', "
        "approved_at = CURRENT_TIMESTAMP WHERE task_id = ?",
        (task_id,)
    )
    task = await fetchone(
        "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
    )
    await callback.message.edit_text(
        f"Задание #{task_id} одобрено!"
    )
    await notify_user(
        bot, task["customer_id"],
        f"Задание #{task_id} ({task['title']}) одобрено!\n"
        "Исполнители уже могут его видеть."
    )


@router.callback_query(F.data.startswith("reject_"))
async def reject_task(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return
    task_id = int(callback.data.split("_")[1])
    await execute(
        "UPDATE tasks SET status = 'rejected' WHERE task_id = ?",
        (task_id,)
    )
    task = await fetchone(
        "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
    )
    await callback.message.edit_text(
        f"Задание #{task_id} отклонено."
    )
    await notify_user(
        bot, task["customer_id"],
        f"Задание #{task_id} ({task['title']}) отклонено.\n"
        "Попробуйте изменить описание."
    )


@router.callback_query(F.data.startswith("revision_"))
async def request_revision(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return
    task_id = int(callback.data.split("_")[1])
    task = await fetchone(
        "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
    )
    await callback.message.edit_text(
        f"Запрос правки по заданию #{task_id} отправлен."
    )
    await notify_user(
        bot, task["customer_id"],
        f"Задание #{task_id} ({task['title']}) требует правки.\n"
        "Уточните описание и создайте заново."
    )


@router.callback_query(F.data == "admin_disputes")
async def admin_disputes(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    disputes = await fetchall(
        "SELECT d.*, t.title, t.budget, t.customer_id, t.executor_id "
        "FROM disputes d "
        "JOIN tasks t ON d.task_id = t.task_id "
        "WHERE d.status = 'open'"
    )
    if not disputes:
        return await callback.message.edit_text(
            "Нет открытых споров!",
            reply_markup=admin_menu()
        )
    for d in disputes:
        text = (
            f"Спор #{d['dispute_id']}\n"
            f"Задание #{d['task_id']}: {d['title']}\n"
            f"Сумма: {d['budget']:.0f} руб\n"
            f"Причина: {d['reason']}"
        )
        await callback.message.answer(
            text,
            reply_markup=dispute_resolution(d["dispute_id"])
        )


@router.callback_query(F.data.startswith("resolve_"))
async def resolve_dispute(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        return
    parts = callback.data.split("_")
    resolution = parts[1]
    dispute_id = int(parts[2])
    dispute = await fetchone(
        "SELECT d.*, t.budget, t.customer_id, t.executor_id, t.task_id "
        "FROM disputes d "
        "JOIN tasks t ON d.task_id = t.task_id "
        "WHERE d.dispute_id = ?",
        (dispute_id,)
    )
    if not dispute:
        return await callback.answer("Не найден")
    budget = dispute["budget"]
    result_text = ""
    if resolution == "customer":
        await execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (budget, dispute["customer_id"])
        )
        result_text = f"{budget:.0f} руб возвращены заказчику"
    elif resolution == "executor":
        await execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (budget, dispute["executor_id"])
        )
        result_text = f"{budget:.0f} руб переведены исполнителю"
    elif resolution == "split":
        half = budget / 2
        await execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (half, dispute["customer_id"])
        )
        await execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (half, dispute["executor_id"])
        )
        result_text = f"По {half:.0f} руб каждому"
    await execute(
        "UPDATE disputes SET status = 'resolved', resolution = ? "
        "WHERE dispute_id = ?",
        (resolution, dispute_id)
    )
    await execute(
        "UPDATE tasks SET status = 'resolved' WHERE task_id = ?",
        (dispute["task_id"],)
    )
    await execute(
        "UPDATE transactions SET status = 'resolved' WHERE task_id = ?",
        (dispute["task_id"],)
    )
    await callback.message.edit_text(
        f"Спор #{dispute_id} решен!\n{result_text}"
    )
    for uid in [dispute["customer_id"], dispute["executor_id"]]:
        await notify_user(
            bot, uid,
            f"Спор по заданию #{dispute['task_id']} решен.\n{result_text}"
        )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    users = await fetchone("SELECT COUNT(*) as c FROM users")
    total_tasks = await fetchone("SELECT COUNT(*) as c FROM tasks")
    completed = await fetchone(
        "SELECT COUNT(*) as c FROM tasks WHERE status = 'completed'"
    )
    revenue = await fetchone(
        "SELECT COALESCE(SUM(amount), 0) as s "
        "FROM transactions WHERE status = 'released'"
    )
    text = (
        "Статистика\n\n"
        f"Пользователей: {users['c']}\n"
        f"Всего заданий: {total_tasks['c']}\n"
        f"Завершено: {completed['c']}\n"
        f"Оборот: {revenue['s']:.0f} руб"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu())


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    users = await fetchall(
        "SELECT * FROM users ORDER BY registered_at DESC LIMIT 20"
    )
    text = "Пользователи:\n\n"
    for u in users:
        username = u['username'] or 'нет'
        text += (
            f"{u['full_name']} (tg: {username}) "
            f"| {u['role']} | {u['balance']:.0f} руб\n"
        )
    await callback.message.edit_text(text, reply_markup=admin_menu())


@router.callback_query(F.data == "admin_active")
async def admin_active(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    tasks = await fetchall(
        "SELECT t.*, u1.full_name as cust "
        "FROM tasks t "
        "LEFT JOIN users u1 ON t.customer_id = u1.user_id "
        "WHERE t.status IN ('in_progress', 'done_pending') "
        "ORDER BY t.created_at DESC"
    )
    if not tasks:
        return await callback.message.edit_text(
            "Нет активных заданий.",
            reply_markup=admin_menu()
        )
    text = "Активные задания:\n\n"
    for t in tasks:
        text += (
            f"#{t['task_id']} - {t['title']}\n"
            f"  {t['budget']:.0f} руб | {t['status']}\n\n"
        )
    await callback.message.edit_text(text, reply_markup=admin_menu())