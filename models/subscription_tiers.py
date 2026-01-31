"""
Модели уровней подписки и их возможности.
"""
from dataclasses import dataclass
from typing import Dict
from config import config


@dataclass
class SubscriptionTier:
    """Модель уровня подписки"""
    name: str
    display_name: str
    price: int  # в тенге
    duration_days: int
    max_searches_per_day: int  # -1 = безлимит
    max_cars_in_garage: int  # -1 = безлимит
    can_view_all_reviews: bool
    can_export_pdf: bool
    can_see_analytics: bool
    priority_support: bool
    
    def get_description(self) -> str:
        """Возвращает описание подписки"""
        features = []
        
        if self.max_searches_per_day == -1:
            features.append("✅ Неограниченные поиски")
        else:
            features.append(f"✅ До {self.max_searches_per_day} поисков в день")
        
        if self.max_cars_in_garage == -1:
            features.append("✅ Неограниченное количество авто в гараже")
        else:
            features.append(f"✅ До {self.max_cars_in_garage} авто в гараже")
        
        if self.can_view_all_reviews:
            features.append("✅ Просмотр всех отзывов")
        else:
            features.append("❌ Только первый отзыв")
        
        if self.can_export_pdf:
            features.append("✅ Экспорт в PDF")
        
        if self.can_see_analytics:
            features.append("✅ Аналитика и статистика")
        
        if self.priority_support:
            features.append("✅ Приоритетная поддержка")
        
        return "\n".join(features)


# Определение всех уровней подписки
SUBSCRIPTION_TIERS: Dict[str, SubscriptionTier] = {
    'free': SubscriptionTier(
        name='free',
        display_name='🆓 Бесплатный',
        price=0,
        duration_days=0,
        max_searches_per_day=config.MAX_SEARCHES_PER_DAY_FREE,
        max_cars_in_garage=1,
        can_view_all_reviews=False,
        can_export_pdf=False,
        can_see_analytics=False,
        priority_support=False
    ),
    
    'basic': SubscriptionTier(
        name='basic',
        display_name='⭐ Базовый',
        price=config.PRICE_BASIC,
        duration_days=30,
        max_searches_per_day=-1,  # безлимит
        max_cars_in_garage=3,
        can_view_all_reviews=True,
        can_export_pdf=False,
        can_see_analytics=False,
        priority_support=False
    ),
    
    'premium': SubscriptionTier(
        name='premium',
        display_name='💎 Премиум',
        price=config.PRICE_PREMIUM,
        duration_days=30,
        max_searches_per_day=-1,
        max_cars_in_garage=-1,  # безлимит
        can_view_all_reviews=True,
        can_export_pdf=True,
        can_see_analytics=True,
        priority_support=True
    ),
    
    'business': SubscriptionTier(
        name='business',
        display_name='🏢 Бизнес',
        price=config.PRICE_BUSINESS,
        duration_days=30,
        max_searches_per_day=-1,
        max_cars_in_garage=-1,
        can_view_all_reviews=True,
        can_export_pdf=True,
        can_see_analytics=True,
        priority_support=True
    )
}


def get_tier(tier_name: str) -> SubscriptionTier:
    """Получает объект подписки по имени"""
    return SUBSCRIPTION_TIERS.get(tier_name, SUBSCRIPTION_TIERS['free'])


def can_perform_action(tier_name: str, action: str, current_usage: int = 0) -> tuple[bool, str]:
    """
    Проверяет, может ли пользователь выполнить действие.
    
    Args:
        tier_name: Уровень подписки
        action: Действие (search, add_car, view_all_reviews, etc.)
        current_usage: Текущее использование (для лимитов)
        
    Returns:
        (разрешено, сообщение об ошибке)
    """
    tier = get_tier(tier_name)
    
    if action == 'search':
        if tier.max_searches_per_day == -1:
            return True, ""
        
        if current_usage >= tier.max_searches_per_day:
            return False, (
                f"❌ Достигнут лимит поисков ({tier.max_searches_per_day}/день)\n\n"
                f"💎 Обновите подписку для безлимитного доступа!"
            )
        
        return True, ""
    
    elif action == 'add_car':
        if tier.max_cars_in_garage == -1:
            return True, ""
        
        if current_usage >= tier.max_cars_in_garage:
            return False, (
                f"❌ Достигнут лимит авто в гараже ({tier.max_cars_in_garage})\n\n"
                f"💎 Обновите подписку для добавления большего количества авто!"
            )
        
        return True, ""
    
    elif action == 'view_all_reviews':
        if not tier.can_view_all_reviews:
            return False, (
                "🔒 Доступен только первый отзыв\n\n"
                "💎 Оформите подписку для просмотра всех отзывов!"
            )
        return True, ""
    
    elif action == 'export_pdf':
        if not tier.can_export_pdf:
            return False, "🔒 Экспорт в PDF доступен только в Премиум и Бизнес подписках"
        return True, ""
    
    elif action == 'analytics':
        if not tier.can_see_analytics:
            return False, "🔒 Аналитика доступна только в Премиум и Бизнес подписках"
        return True, ""
    
    return True, ""
