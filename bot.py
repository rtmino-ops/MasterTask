import asyncio
import logging
import traceback

from config import BOT_TOKEN  # 👈 ВАЖНО: сюда

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def main():
    try:
        logging.info("Загружаю config...")
        logging.info(f"Токен: {BOT_TOKEN[:10]}..." if BOT_TOKEN else "ТОКЕН ПУСТОЙ!")

        if not BOT_TOKEN:
            logging.error("BOT_TOKEN не найден! Проверь .env файл")
            return

        logging.info("Загр��жаю базу данных...")
        from database.db import init_db
        await init_db()

        logging.info("Создаю бота...")
        from aiogram import Bot, Dispatcher
        from aiogram.fsm.storage.memory import MemoryStorage

        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        logging.info("Подключаю хендлеры...")
        from handlers import common, customer, executor, admin
        dp.include_router(common.router)
        dp.include_router(customer.router)
        dp.include_router(executor.router)
        dp.include_router(admin.router)

        logging.info("🤖 Бот запускается...")
        await dp.start_polling(bot)

    except Exception as e:
        logging.error(f"ОШИБКА: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы закрыть...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    except Exception as e:
        print(f"КРИТИЧЕ��КАЯ ОШИБКА: {e}")
        traceback.print_exc()
        input("Нажми Enter чтобы закрыть...")