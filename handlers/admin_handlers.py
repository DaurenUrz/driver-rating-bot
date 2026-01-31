"""
Обработчики админ-панели.
"""
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db_manager import db
from utils.logger import logger
from utils.formatters import format_admin_stats
from utils.validators import clean_plate
from config import config
from keyboards.inline_keyboards import get_admin_panel_keyboard

router = Router()


# --- СОСТОЯНИЯ ---
class AdminState(StatesGroup):
    waiting_broadcast = State()
    waiting_delete_plate = State()
    waiting_user_search = State()
    waiting_ban_user = State()


# --- ПРОВЕРКА АДМИНА ---
def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return user_id == config.ADMIN_ID


# --- АДМИН-ПАНЕЛЬ ---
@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Открывает админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "🛠 <b>Панель управления</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )
    
    logger.info(f"Админ {message.from_user.id} открыл панель управления")


# --- СТАТИСТИКА ---
@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показывает статистику бота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    stats = await db.get_admin_stats()
    text = format_admin_stats(stats)
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# --- ПОИСК ПОЛЬЗОВАТЕЛЯ ---
@router.callback_query(F.data == "admin_find_user")
async def find_user_start(callback: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.answer(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите @username или ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_user_search)
    await callback.answer()


@router.message(AdminState.waiting_user_search)
async def find_user_process(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    search_query = message.text.replace("@", "").strip()
    
    # Поиск в БД
    async with db.acquire() as conn:
        if search_query.isdigit():
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE user_id = $1',
                int(search_query)
            )
        else:
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE username ILIKE $1',
                search_query
            )
    
    if not user:
        await message.answer("❌ Пользователь не найден в базе")
        await state.clear()
        return
    
    # Получаем дополнительную информацию
    tier_name = await db.get_user_subscription_tier(user['user_id'])
    usage = await db.get_daily_usage(user['user_id'])
    
    # Количество отзывов
    async with db.acquire() as conn:
        review_count = await conn.fetchval(
            'SELECT COUNT(*) FROM reviews WHERE user_id = $1 AND is_deleted = FALSE',
            user['user_id']
        )
        
        car_count = await conn.fetchval(
            'SELECT COUNT(*) FROM subscriptions WHERE user_id = $1',
            user['user_id']
        )
    
    # Формируем ответ
    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"🏷 Username: @{user['username'] if user['username'] else 'нет'}\n"
        f"👤 Имя: {user['full_name']}\n"
        f"📅 Регистрация: {user['joined_at'].strftime('%d.%m.%Y')}\n"
        f"⏰ Последняя активность: {user['last_active'].strftime('%d.%m.%Y %H:%M')}\n\n"
        f"💎 Подписка: {tier_name}\n"
        f"✍️ Отзывов: {review_count}\n"
        f"🚗 Авто в гараже: {car_count}\n\n"
        f"📊 <b>Сегодня:</b>\n"
        f"🔍 Поисков: {usage['searches']}\n"
        f"✍️ Отзывов: {usage['reviews']}\n\n"
        f"🚫 Забанен: {'Да' if user['is_banned'] else 'Нет'}"
    )
    
    await message.answer(text, parse_mode="HTML")
    await state.clear()


# --- РАССЫЛКА ---
@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.answer(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Введите текст для рассылки всем пользователям:\n\n"
        "⚠️ Используйте HTML-разметку для форматирования",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_broadcast)
    await callback.answer()


@router.message(AdminState.waiting_broadcast)
async def broadcast_process(message: Message, state: FSMContext):
    """Обработка рассылки"""
    if not is_admin(message.from_user.id):
        return
    
    broadcast_text = message.text
    
    # Получаем всех пользователей
    async with db.acquire() as conn:
        users = await conn.fetch('SELECT user_id FROM users WHERE is_banned = FALSE')
    
    total = len(users)
    success = 0
    failed = 0
    
    status_msg = await message.answer(
        f"📤 Начинаю рассылку...\n\n"
        f"Всего пользователей: {total}"
    )
    
    bot = Bot(token=config.BOT_TOKEN)
    
    # Рассылка с прогрессом
    for i, user in enumerate(users, 1):
        try:
            await bot.send_message(user['user_id'], broadcast_text, parse_mode="HTML")
            success += 1
            
            # Обновляем статус каждые 10 пользователей
            if i % 10 == 0:
                await status_msg.edit_text(
                    f"📤 Рассылка в процессе...\n\n"
                    f"Отправлено: {i}/{total}\n"
                    f"✅ Успешно: {success}\n"
                    f"❌ Ошибок: {failed}"
                )
            
            # Задержка чтобы не словить лимит
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить сообщение пользователю {user['user_id']}: {e}")
    
    # Итоговый отчет
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Статистика:\n"
        f"Всего пользователей: {total}\n"
        f"✅ Доставлено: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"📈 Успешность: {(success/total*100):.1f}%",
        parse_mode="HTML"
    )
    
    await state.clear()
    logger.info(f"Рассылка завершена: {success}/{total} успешно")


# --- УДАЛЕНИЕ НОМЕРА ---
@router.callback_query(F.data == "admin_del_plate")
async def delete_plate_start(callback: CallbackQuery, state: FSMContext):
    """Начало удаления номера"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.answer(
        "🗑 <b>Удаление номера</b>\n\n"
        "Введите госномер для удаления всех отзывов:\n\n"
        "⚠️ Это действие нельзя отменить!",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_delete_plate)
    await callback.answer()


@router.message(AdminState.waiting_delete_plate)
async def delete_plate_process(message: Message, state: FSMContext):
    """Обработка удаления номера"""
    if not is_admin(message.from_user.id):
        return
    
    plate = clean_plate(message.text)
    
    # Удаляем отзывы (мягкое удаление)
    count = await db.delete_reviews_by_plate(plate)
    
    if count > 0:
        await message.answer(
            f"✅ <b>Номер очищен</b>\n\n"
            f"🗑 Удалено отзывов: {count}\n"
            f"🚗 Номер: <code>{plate}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"❌ По номеру {plate} не найдено отзывов")
    
    await state.clear()


# --- ФИНАНСЫ ---
@router.callback_query(F.data == "admin_finance")
async def show_finance(callback: CallbackQuery):
    """Показывает финансовую статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    async with db.acquire() as conn:
        # Статистика по периодам
        today_revenue = await conn.fetchval('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE status = 'confirmed' AND DATE(confirmed_at) = CURRENT_DATE
        ''')
        
        week_revenue = await conn.fetchval('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE status = 'confirmed' AND confirmed_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        ''')
        
        month_revenue = await conn.fetchval('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE status = 'confirmed' AND confirmed_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
        ''')
        
        total_revenue = await conn.fetchval('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE status = 'confirmed'
        ''')
        
        # Статистика по тарифам
        tier_stats = await conn.fetch('''
            SELECT tier, COUNT(*) as count, SUM(amount) as revenue
            FROM transactions
            WHERE status = 'confirmed'
            GROUP BY tier
            ORDER BY revenue DESC
        ''')
        
        # Ожидающие подтверждения
        pending = await conn.fetchval('''
            SELECT COUNT(*) FROM transactions
            WHERE status = 'pending'
        ''')
    
    # Формируем отчет
    text = (
        f"💰 <b>Финансовая статистика</b>\n\n"
        f"📅 <b>Доход:</b>\n"
        f"Сегодня: {today_revenue:,} ₸\n"
        f"За неделю: {week_revenue:,} ₸\n"
        f"За месяц: {month_revenue:,} ₸\n"
        f"Всего: {total_revenue:,} ₸\n\n"
        f"📊 <b>По тарифам:</b>\n"
    )
    
    for stat in tier_stats:
        text += f"{stat['tier']}: {stat['count']} шт. ({stat['revenue']:,} ₸)\n"
    
    text += f"\n⏳ Ожидают подтверждения: {pending}"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# --- БАН/РАЗБАН ---
@router.callback_query(F.data == "admin_ban")
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    """Начало бана пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.answer(
        "🚫 <b>Бан/Разбан пользователя</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.waiting_ban_user)
    await callback.answer()


@router.message(AdminState.waiting_ban_user)
async def ban_user_process(message: Message, state: FSMContext):
    """Обработка бана пользователя"""
    if not is_admin(message.from_user.id):
        return
    
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID пользователя")
        return
    
    user_id = int(message.text)
    
    # Проверяем статус
    async with db.acquire() as conn:
        is_banned = await conn.fetchval(
            'SELECT is_banned FROM users WHERE user_id = $1',
            user_id
        )
        
        if is_banned is None:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return
        
        # Переключаем статус
        new_status = not is_banned
        
        await conn.execute(
            'UPDATE users SET is_banned = $1 WHERE user_id = $2',
            new_status, user_id
        )
    
    if new_status:
        await message.answer(f"🚫 Пользователь {user_id} заблокирован")
        logger.warning(f"Пользователь {user_id} заблокирован админом")
    else:
        await message.answer(f"✅ Пользователь {user_id} разблокирован")
        logger.info(f"Пользователь {user_id} разблокирован админом")
    
    await state.clear()
