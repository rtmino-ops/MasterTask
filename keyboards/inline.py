from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════════════════════════════════
# ГЛАВНЫЕ МЕНЮ
# ══════════════════════════════════════════

def role_selection():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👔 Я заказчик", callback_data="role_customer")],
        [InlineKeyboardButton(text="🔧 Я исполнитель", callback_data="role_executor")],
        [InlineKeyboardButton(text="🔄 Оба варианта", callback_data="role_both")],
    ])


def main_menu_customer():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать задание", callback_data="create_task")],
        [InlineKeyboardButton(text="📋 Мои задания", callback_data="my_tasks_customer")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def main_menu_executor():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти задания", callback_data="browse_tasks")],
        [InlineKeyboardButton(text="📋 Мои отклики", callback_data="my_responses")],
        [InlineKeyboardButton(text="🏗 Активные задания", callback_data="my_active_tasks")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def main_menu_both():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать задание", callback_data="create_task")],
        [InlineKeyboardButton(text="🔍 Найти задания", callback_data="browse_tasks")],
        [InlineKeyboardButton(text="📋 Мои задания", callback_data="my_tasks_customer")],
        [InlineKeyboardButton(text="📋 Мои отклики", callback_data="my_responses")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ])


def get_menu_by_role(role: str):
    if role == "customer":
        return main_menu_customer()
    elif role == "executor":
        return main_menu_executor()
    else:
        return main_menu_both()


def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное м��ню", callback_data="main_menu")],
    ])


# ══════════════════════════════════════════
# СОЗДАНИЕ ЗАДАНИЯ
# ══════════════════════════════════════════

def task_categories():
    categories = [
        ("🔧 Ремонт", "repair"),
        ("🚚 Доставка", "delivery"),
        ("💻 IT/Программирование", "it"),
        ("📐 Дизайн", "design"),
        ("📝 Копирайтинг", "copywriting"),
        ("📊 Маркетинг", "marketing"),
        ("🏠 Уборка", "cleaning"),
        ("📦 Переезд", "moving"),
        ("🔌 Электрика", "electric"),
        ("🪠 Сантехника", "plumbing"),
        ("📚 Репетиторство", "tutoring"),
        ("📸 Фото/Видео", "photo"),
        ("🔑 Другое", "other"),
    ]
    builder = InlineKeyboardBuilder()
    for text, data in categories:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"cat_{data}"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_create"))
    return builder.as_markup()


def task_confirm():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_task")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_task")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_create")],
    ])


# ══════════════════════════════════════════
# ЛЕНТА ЗАДАНИЙ ДЛЯ ИСПОЛНИТЕЛЕЙ
# ══════════════════════════════════════════

def task_card_executor(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Готов взяться", callback_data=f"respond_{task_id}")],
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data=f"skip_{task_id}")],
    ])


def no_more_tasks():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="browse_tasks")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")],
    ])


# ══════════════════════════════════════════
# ЗАКАЗЧИК: ПРОСМОТР ОТКЛИКОВ
# ══════════════════════════════════════════

def task_actions_customer(task_id: int, has_responses: bool = False):
    buttons = []
    if has_responses:
        buttons.append([InlineKeyboardButton(
            text="👥 Смотреть отклики",
            callback_data=f"view_responses_{task_id}"
        )])
    buttons.append([InlineKeyboardButton(
        text="❌ Отменить задание",
        callback_data=f"cancel_task_{task_id}"
    )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="my_tasks_customer"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def response_card(response_id: int, task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Выбрать этого исполнителя",
            callback_data=f"pick_{response_id}"
        )],
        [InlineKeyboardButton(
            text="➡️ Следующий",
            callback_data=f"next_resp_{task_id}_{response_id}"
        )],
    ])


# ══════════════════════════════════════════
# ОПЛАТА
# ══════════════════════════════════════════

def payment_keyboard(task_id: int, amount: float):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Оплатить {amount:.0f}₽",
            callback_data=f"pay_{task_id}"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_pay_{task_id}")],
    ])


# ══════════════════════════════════════════
# ЗАВЕРШЕНИЕ РАБОТЫ
# ══════════════════════════════════════════

def executor_work_menu(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Работа выполнена", callback_data=f"done_{task_id}")],
        [InlineKeyboardButton(text="💬 Написать заказчику", callback_data=f"msg_customer_{task_id}")],
    ])


def completion_keyboard(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить выполнение", callback_data=f"complete_{task_id}")],
        [InlineKeyboardButton(text="⚠️ Открыть спор", callback_data=f"dispute_{task_id}")],
    ])


def review_stars():
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text="⭐" * i, callback_data=f"stars_{i}"))
    builder.adjust(1)
    return builder.as_markup()


# ══════════════════════════════════════════
# АДМИН
# ══════════════════════════════════════════

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 На модерации", callback_data="admin_pending")],
        [InlineKeyboardButton(text="⚠️ Споры", callback_data="admin_disputes")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔨 Все активные", callback_data="admin_active")],
    ])


def admin_task_review(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{task_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{task_id}"),
        ],
        [InlineKeyboardButton(text="✏️ Запросить правку", callback_data=f"revision_{task_id}")],
    ])


def dispute_resolution(dispute_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💰 Вернуть заказчику",
            callback_data=f"resolve_customer_{dispute_id}"
        )],
        [InlineKeyboardButton(
            text="💰 Отдать исполнителю",
            callback_data=f"resolve_executor_{dispute_id}"
        )],
        [InlineKeyboardButton(
            text="💰 Разделить 50/50",
            callback_data=f"resolve_split_{dispute_id}"
        )],
    ])