"""
Driver Rating KZ Pro - Telegram Bot
Главный файл запуска бота
"""
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from config import config
from database.db_manager import db
from utils.logger import logger

# Импортируем роутеры
from handlers import user_handlers, payment_handlers, admin_handlers


async def set_bot_commands(bot: Bot):
    """Устанавливает команды бота в меню"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="search", description="🔍 Проверить номер"),
        BotCommand(command="review", description="✍️ Оставить отзыв"),
        BotCommand(command="my_cars", description="🚗 Мой гараж"),
    ]
    
    # Добавляем админские команды для админа
    admin_commands = commands + [
        BotCommand(command="admin", description="🛠 Админ-панель")
    ]
    
    await bot.set_my_commands(commands)
    await bot.set_my_commands(admin_commands, scope={"type": "chat", "chat_id": config.ADMIN_ID})
    
    logger.info("✅ Команды бота установлены")


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("🚀 Запуск бота...")
    
    # Инициализируем пул соединений с БД
    await db.init_pool()
    
    # Создаем таблицы если их нет
    await db.init_tables()
    
    # Устанавливаем команды
    await set_bot_commands(bot)
    
    # Уведомляем админа о запуске
    try:
        await bot.send_message(
            config.ADMIN_ID,
            "✅ <b>Бот запущен!</b>\n\n"
            "Все системы работают нормально.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа о запуске: {e}")
    
    logger.info("✅ Бот успешно запущен!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("🛑 Остановка бота...")
    
    # Закрываем пул соединений
    await db.close_pool()
    
    # Уведомляем админа об остановке
    try:
        await bot.send_message(
            config.ADMIN_ID,
            "⚠️ <b>Бот остановлен</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить админа об остановке: {e}")
    
    logger.info("✅ Бот остановлен")


async def main():
    """Главная функция запуска бота"""
    
    # Проверяем конфигурацию
    if not config.validate():
        logger.error("❌ Ошибка конфигурации. Бот не запущен.")
        sys.exit(1)
    
    # Создаем бота и диспетчер
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем роутеры
    dp.include_router(user_handlers.router)
    dp.include_router(payment_handlers.router)
    dp.include_router(admin_handlers.router)
    
    # Регистрируем startup/shutdown хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Запускаем polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("⌨️ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"💥 Фатальная ошибка: {e}")
        sys.exit(1)
