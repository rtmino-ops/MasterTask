from aiogram import Bot


async def notify_user(bot: Bot, user_id: int, text: str, reply_markup=None):
    try:
        await bot.send_message(
            user_id,
            text,
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        print(f"Notify error {user_id}: {e}")
        return False


async def notify_admins(bot: Bot, admin_ids: list, text: str, reply_markup=None):
    for admin_id in admin_ids:
        await notify_user(bot, admin_id, text, reply_markup)