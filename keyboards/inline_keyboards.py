"""
Inline-клавиатуры для бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора оценки"""
    buttons = [
        [InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate_{i}") for i in range(1, 6)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_share_keyboard(plate: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой поделиться"""
    buttons = [
        [InlineKeyboardButton(text="📲 Поделиться", callback_data=f"share_{plate}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_unlock_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для разблокировки всех отзывов"""
    buttons = [
        [InlineKeyboardButton(text="🔓 Открыть все отзывы", callback_data="buy_basic")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subscription_tiers_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с выбором подписки"""
    buttons = [
        [InlineKeyboardButton(text="⭐ Базовый (500 ₸/мес)", callback_data="buy_basic")],
        [InlineKeyboardButton(text="💎 Премиум (1000 ₸/мес)", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🏢 Бизнес (2500 ₸/мес)", callback_data="buy_business")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_confirmation_keyboard(user_id: int, tier: str, payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения платежа админом"""
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_payment_{user_id}_{tier}_{payment_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{payment_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔍 Найти юзера", callback_data="admin_find_user")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🗑 Удалить номер", callback_data="admin_del_plate")
        ],
        [
            InlineKeyboardButton(text="💰 Финансы", callback_data="admin_finance"),
            InlineKeyboardButton(text="🚫 Бан/Разбан", callback_data="admin_ban")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_location_map_keyboard(latitude: float, longitude: float) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой открыть на карте"""
    url = f"https://www.google.com/maps?q={latitude},{longitude}"
    buttons = [
        [InlineKeyboardButton(text="📍 Открыть на карте", url=url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """Клавиатура для реферальной программы"""
    buttons = [
        [InlineKeyboardButton(text="📲 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_my_cars_keyboard(plates: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура со списком авто пользователя"""
    buttons = []
    
    for plate in plates:
        buttons.append([
            InlineKeyboardButton(text=f"🚗 {plate}", callback_data=f"view_car_{plate}"),
            InlineKeyboardButton(text="🗑", callback_data=f"remove_car_{plate}")
        ])
    
    buttons.append([InlineKeyboardButton(text="➕ Добавить авто", callback_data="add_car")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Простая кнопка отмены"""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
