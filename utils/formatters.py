"""
Форматтеры для красивого отображения сообщений.
"""
from typing import List, Dict, Any
from datetime import datetime


def format_review_header(plate: str, region: str, avg_rating: float, review_count: int) -> str:
    """
    Форматирует заголовок результатов поиска.
    
    Args:
        plate: Госномер
        region: Название региона
        avg_rating: Средний рейтинг
        review_count: Количество отзывов
        
    Returns:
        Отформатированный заголовок
    """
    stars = '⭐' * int(round(avg_rating))
    
    return (
        f"🚘 <b>{plate}</b> ({region})\n"
        f"📊 Рейтинг: {stars} ({avg_rating:.1f}/5)\n"
        f"💬 Отзывов: {review_count}"
    )


def format_single_review(index: int, rating: int, comment: str, has_media: bool = False) -> str:
    """
    Форматирует один отзыв.
    
    Args:
        index: Номер отзыва
        rating: Оценка
        comment: Текст комментария
        has_media: Есть ли фото/видео
        
    Returns:
        Отформатированный отзыв
    """
    stars = '⭐' * rating
    media_icon = "📸 " if has_media else ""
    
    return (
        f"<b>Отзыв #{index}</b>: {stars}\n"
        f"{media_icon}<i>{comment}</i>"
    )


def format_user_stats(stats: Dict[str, Any]) -> str:
    """
    Форматирует статистику пользователя.
    
    Args:
        stats: Словарь со статистикой
        
    Returns:
        Отформатированная статистика
    """
    return (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"🔍 Поисков: {stats.get('searches', 0)}\n"
        f"✍️ Отзывов: {stats.get('reviews', 0)}\n"
        f"🚗 Авто в гараже: {stats.get('cars', 0)}\n"
        f"📅 С нами с: {stats.get('joined_date', 'N/A')}"
    )


def format_subscription_info(tier: str, expires_at: datetime = None) -> str:
    """
    Форматирует информацию о подписке.
    
    Args:
        tier: Уровень подписки (free, basic, premium, business)
        expires_at: Дата окончания подписки
        
    Returns:
        Отформатированная информация
    """
    tier_names = {
        'free': '🆓 Бесплатный',
        'basic': '⭐ Базовый',
        'premium': '💎 Премиум',
        'business': '🏢 Бизнес'
    }
    
    tier_name = tier_names.get(tier, tier)
    
    if expires_at:
        days_left = (expires_at - datetime.now()).days
        expiry_text = f"\n⏰ Осталось дней: {days_left}"
    else:
        expiry_text = ""
    
    return f"📦 <b>Ваша подписка:</b> {tier_name}{expiry_text}"


def format_payment_instructions(amount: int, payment_id: str, kaspi_phone: str) -> str:
    """
    Форматирует инструкции по оплате.
    
    Args:
        amount: Сумма в тенге
        payment_id: Уникальный ID платежа
        kaspi_phone: Номер Kaspi
        
    Returns:
        Инструкции по оплате
    """
    return (
        f"💳 <b>Оплата подписки</b>\n\n"
        f"💰 Сумма: <b>{amount} ₸</b>\n"
        f"📱 Kaspi: <code>{kaspi_phone}</code>\n\n"
        f"🔑 ID платежа: <code>{payment_id}</code>\n\n"
        f"📸 После оплаты пришлите скриншот чека\n"
        f"⚠️ Обязательно укажите ID платежа в комментарии!"
    )


def format_admin_stats(stats: Dict[str, Any]) -> str:
    """
    Форматирует статистику для админа.
    
    Args:
        stats: Словарь со статистикой
        
    Returns:
        Отформатированная статистика
    """
    return (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
        f"📝 Всего отзывов: {stats.get('total_reviews', 0)}\n"
        f"🚗 Уникальных номеров: {stats.get('unique_plates', 0)}\n"
        f"💰 Активных подписок: {stats.get('active_subs', 0)}\n"
        f"💵 Доход за месяц: {stats.get('monthly_revenue', 0)} ₸\n"
        f"📈 Новых за неделю: {stats.get('new_users_week', 0)}"
    )


def format_car_list(cars: List[Dict[str, Any]]) -> str:
    """
    Форматирует список автомобилей в гараже.
    
    Args:
        cars: Список словарей с информацией об авто
        
    Returns:
        Отформатированный список
    """
    if not cars:
        return "🚗 <b>Ваш гараж пуст</b>\n\nДобавьте свой автомобиль, чтобы получать уведомления о новых отзывах!"
    
    car_list = "\n".join([
        f"• <code>{car['plate']}</code> - {car.get('region', 'N/A')} ({car.get('review_count', 0)} отзывов)"
        for car in cars
    ])
    
    return f"🚗 <b>Ваши автомобили:</b>\n\n{car_list}"
