"""
Модуль конфигурации для Driver Rating KZ Pro Bot.
Загружает настройки из переменных окружения с валидацией.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Config:
    """Централизованная конфигурация бота"""
    
    # Telegram Bot
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    ADMIN_ID: int = int(os.getenv('ADMIN_ID', '0'))
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    
    # Payment
    KASPI_PHONE: str = os.getenv('KASPI_PHONE', '+77770000000')
    STRIPE_API_KEY: Optional[str] = os.getenv('STRIPE_API_KEY')
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'bot.log')
    
    # Features
    ENABLE_REFERRAL_SYSTEM: bool = os.getenv('ENABLE_REFERRAL_SYSTEM', 'true').lower() == 'true'
    ENABLE_ANALYTICS: bool = os.getenv('ENABLE_ANALYTICS', 'true').lower() == 'true'
    
    # Rate Limiting
    MAX_SEARCHES_PER_DAY_FREE: int = int(os.getenv('MAX_SEARCHES_PER_DAY_FREE', '3'))
    MAX_REVIEWS_PER_DAY: int = int(os.getenv('MAX_REVIEWS_PER_DAY', '10'))
    
    # Subscription Pricing (в тенге)
    PRICE_BASIC: int = int(os.getenv('PRICE_BASIC', '500'))
    PRICE_PREMIUM: int = int(os.getenv('PRICE_PREMIUM', '1000'))
    PRICE_BUSINESS: int = int(os.getenv('PRICE_BUSINESS', '2500'))
    
    # Регионы Казахстана
    KZ_REGIONS = {
        "01": "Астана", "02": "Алматы", "03": "Акмолинская обл.", "04": "Актюбинская обл.",
        "05": "Алматинская обл.", "06": "Атырауская обл.", "07": "ЗКО", "08": "Жамбылская обл.",
        "09": "Карагандинская обл.", "10": "Костанайская обл.", "11": "Кызылординская обл.",
        "12": "Мангистауская обл.", "13": "Туркестанская обл.", "14": "Павлодарская обл.",
        "15": "СКО", "16": "ВКО", "17": "Шымкент", "18": "Абайская обл.", "19": "Жетысуская обл.", 
        "20": "Улытауская обл."
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет наличие обязательных настроек"""
        errors = []
        
        if not cls.BOT_TOKEN:
            errors.append("❌ BOT_TOKEN не установлен")
        
        if not cls.ADMIN_ID:
            errors.append("❌ ADMIN_ID не установлен")
        
        if not cls.DATABASE_URL:
            errors.append("❌ DATABASE_URL не установлен")
        
        if errors:
            print("\n🚨 ОШИБКИ КОНФИГУРАЦИИ:\n")
            for error in errors:
                print(error)
            print("\n💡 Создайте файл .env на основе .env.example\n")
            return False
        
        return True
    
    @classmethod
    def get_region_name(cls, plate: str) -> str:
        """Возвращает название региона по номеру"""
        region_code = plate[-2:] if len(plate) >= 2 else ""
        return cls.KZ_REGIONS.get(region_code, "Регион не определен")


# Экспортируем экземпляр конфигурации
config = Config()
