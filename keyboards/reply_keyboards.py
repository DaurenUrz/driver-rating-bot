"""
Reply-клавиатуры для основного меню.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard(is_premium: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню (адаптируется под статус пользователя).
    
    Args:
        is_premium: Есть ли у пользователя премиум подписка
    """
    buttons = [
        [KeyboardButton(text="🔍 Проверить номер"), KeyboardButton(text="✍️ Оставить отзыв")],
        [KeyboardButton(text="🚗 Мой гараж"), KeyboardButton(text="💎 Подписка")]
    ]
    
    if is_premium:
        buttons.append([KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🎁 Пригласить друга")])
    else:
        buttons.append([KeyboardButton(text="🎁 Пригласить друга")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отправки геолокации"""
    buttons = [
        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
        [KeyboardButton(text="⏭ Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой пропустить"""
    buttons = [
        [KeyboardButton(text="⏭ Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    buttons = [
        [KeyboardButton(text="❌ Отменить")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения"""
    buttons = [
        [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
