"""
Обработчики платежей и подписок.
"""
import uuid
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db_manager import db
from utils.logger import logger
from utils.formatters import format_payment_instructions, format_subscription_info
from config import config
from models.subscription_tiers import SUBSCRIPTION_TIERS, get_tier
from keyboards.inline_keyboards import (
    get_subscription_tiers_keyboard,
    get_payment_confirmation_keyboard
)
from keyboards.reply_keyboards import get_main_menu_keyboard

router = Router()


# --- СОСТОЯНИЯ ---
class PaymentForm(StatesGroup):
    waiting_for_screenshot = State()


# --- ПРОСМОТР ПОДПИСКИ ---
@router.message(F.text == "💎 Подписка")
async def view_subscription(message: Message):
    """Показывает информацию о текущей подписке"""
    user_id = message.from_user.id
    
    tier_name = await db.get_user_subscription_tier(user_id)
    tier = get_tier(tier_name)
    
    # Получаем дату окончания
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT expires_at FROM user_subscriptions WHERE user_id = $1',
            user_id
        )
    
    expires_at = row['expires_at'] if row else None
    
    # Формируем сообщение
    text = format_subscription_info(tier_name, expires_at)
    text += "\n\n<b>Возможности вашей подписки:</b>\n\n"
    text += tier.get_description()
    
    if tier_name == 'free':
        text += "\n\n💎 <b>Хотите больше возможностей?</b>\nВыберите подходящий тариф:"
    
    await message.answer(
        text,
        reply_markup=get_subscription_tiers_keyboard() if tier_name == 'free' else None,
        parse_mode="HTML"
    )


# --- ВЫБОР ТАРИФА ---
@router.callback_query(F.data.startswith("buy_"))
async def select_tier(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора тарифа"""
    tier_name = callback.data.replace("buy_", "")
    
    if tier_name not in SUBSCRIPTION_TIERS:
        await callback.answer("❌ Неверный тариф")
        return
    
    tier = get_tier(tier_name)
    
    # Генерируем уникальный ID платежа
    payment_id = str(uuid.uuid4())[:8].upper()
    
    # Сохраняем транзакцию
    async with db.acquire() as conn:
        await conn.execute('''
            INSERT INTO transactions (user_id, amount, tier, payment_id, status)
            VALUES ($1, $2, $3, $4, 'pending')
        ''', callback.from_user.id, tier.price, tier_name, payment_id)
    
    # Сохраняем данные в состояние
    await state.update_data(tier=tier_name, payment_id=payment_id)
    
    # Формируем инструкции
    instructions = format_payment_instructions(tier.price, payment_id, config.KASPI_PHONE)
    instructions += f"\n\n<b>Тариф:</b> {tier.display_name}\n"
    instructions += f"<b>Срок:</b> {tier.duration_days} дней"
    
    await callback.message.answer(instructions, parse_mode="HTML")
    await callback.message.answer(
        "📸 Пришлите скриншот чека после оплаты:",
        parse_mode="HTML"
    )
    
    await state.set_state(PaymentForm.waiting_for_screenshot)
    await callback.answer()
    
    logger.info(f"Пользователь {callback.from_user.id} начал оплату {tier_name} (ID: {payment_id})")


# --- ОТПРАВКА ЧЕКА ---
@router.message(PaymentForm.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext):
    """Обработка скриншота чека"""
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    full_name = message.from_user.full_name
    
    tier_name = data['tier']
    payment_id = data['payment_id']
    tier = get_tier(tier_name)
    
    # Отправляем чек админу на проверку
    caption = (
        f"💳 <b>Новый платеж!</b>\n\n"
        f"👤 Пользователь: {full_name}\n"
        f"🏷 Тег: @{username}\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"📦 Тариф: {tier.display_name}\n"
        f"💰 Сумма: {tier.price} ₸\n"
        f"🔑 ID платежа: <code>{payment_id}</code>\n\n"
        f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        await bot.send_photo(
            config.ADMIN_ID,
            message.photo[-1].file_id,
            caption=caption,
            reply_markup=get_payment_confirmation_keyboard(user_id, tier_name, payment_id),
            parse_mode="HTML"
        )
        
        await message.answer(
            "✅ <b>Чек принят!</b>\n\n"
            "⏳ Ожидайте подтверждения оплаты.\n"
            "Обычно это занимает несколько минут.\n\n"
            "Вы получите уведомление, как только платеж будет подтвержден.",
            parse_mode="HTML"
        )
        
        logger.info(f"Чек от пользователя {user_id} отправлен админу (платеж {payment_id})")
        
    except Exception as e:
        logger.error(f"Ошибка отправки чека админу: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке чека.\n"
            "Попробуйте еще раз или свяжитесь с поддержкой."
        )
    
    await state.clear()


# --- ПОДТВЕРЖДЕНИЕ ПЛАТЕЖА АДМИНОМ ---
@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery):
    """Подтверждение платежа админом"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    # Парсим данные
    parts = callback.data.split("_")
    user_id = int(parts[2])
    tier_name = parts[3]
    payment_id = parts[4]
    
    tier = get_tier(tier_name)
    
    # Обновляем транзакцию
    async with db.acquire() as conn:
        await conn.execute('''
            UPDATE transactions
            SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
            WHERE payment_id = $1
        ''', payment_id)
    
    # Активируем подписку
    await db.set_user_subscription(user_id, tier_name, tier.duration_days)
    
    # Уведомляем пользователя
    bot = Bot(token=config.BOT_TOKEN)
    
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Платеж подтвержден!</b>\n\n"
            f"🎉 Подписка <b>{tier.display_name}</b> активирована!\n"
            f"⏰ Срок действия: {tier.duration_days} дней\n\n"
            f"Спасибо за покупку! 💙\n\n"
            f"Теперь вам доступны все возможности вашего тарифа.",
            reply_markup=get_main_menu_keyboard(is_premium=True),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ПОДТВЕРЖДЕНО</b>",
        parse_mode="HTML"
    )
    
    await callback.answer("✅ Платеж подтвержден")
    
    logger.info(f"Платеж {payment_id} подтвержден. Пользователю {user_id} активирована подписка {tier_name}")


# --- ОТКЛОНЕНИЕ ПЛАТЕЖА ---
@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment(callback: CallbackQuery):
    """Отклонение платежа админом"""
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("❌ Доступ запрещен")
        return
    
    payment_id = callback.data.replace("reject_payment_", "")
    
    # Обновляем транзакцию
    async with db.acquire() as conn:
        user_id = await conn.fetchval('''
            UPDATE transactions
            SET status = 'rejected'
            WHERE payment_id = $1
            RETURNING user_id
        ''', payment_id)
    
    # Уведомляем пользователя
    if user_id:
        bot = Bot(token=config.BOT_TOKEN)
        
        try:
            await bot.send_message(
                user_id,
                "❌ <b>Платеж отклонен</b>\n\n"
                "К сожалению, ваш платеж не был подтвержден.\n"
                "Возможные причины:\n"
                "• Неверная сумма\n"
                "• Неверный получатель\n"
                "• Нечитаемый чек\n\n"
                "Попробуйте еще раз или свяжитесь с поддержкой.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    
    await callback.answer("❌ Платеж отклонен")
    
    logger.warning(f"Платеж {payment_id} отклонен")


# --- ОТМЕНА ---
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.answer(
        "❌ Действие отменено",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()
