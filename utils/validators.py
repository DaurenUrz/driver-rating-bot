"""
Валидаторы для проверки пользовательского ввода.
"""
import re
from typing import Optional


def clean_plate(plate: str) -> str:
    """
    Очищает номер от лишних символов и приводит к верхнему регистру.
    
    Args:
        plate: Исходный номер
        
    Returns:
        Очищенный номер (только буквы и цифры)
    """
    return re.sub(r'[^A-ZА-Я0-9]', '', plate.upper())


def validate_plate(plate: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет корректность казахстанского госномера.
    
    Формат: XXX999XX где X - буква, 9 - цифра
    Последние 2 цифры - код региона (01-20)
    
    Args:
        plate: Номер для проверки
        
    Returns:
        (валиден, сообщение об ошибке)
    """
    cleaned = clean_plate(plate)
    
    # Минимальная длина
    if len(cleaned) < 6:
        return False, "❌ Номер слишком короткий"
    
    # Максимальная длина
    if len(cleaned) > 10:
        return False, "❌ Номер слишком длинный"
    
    # Проверка кода региона
    if len(cleaned) >= 2:
        region_code = cleaned[-2:]
        if not region_code.isdigit():
            return False, "❌ Код региона должен быть числом"
        
        region_num = int(region_code)
        if region_num < 1 or region_num > 20:
            return False, f"❌ Неверный код региона: {region_code}"
    
    return True, None


def validate_rating(rating: int) -> bool:
    """Проверяет корректность оценки (1-5)"""
    return 1 <= rating <= 5


def validate_comment(comment: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет комментарий на допустимость.
    
    Args:
        comment: Текст комментария
        
    Returns:
        (валиден, сообщение об ошибке)
    """
    if not comment or not comment.strip():
        return False, "❌ Комментарий не может быть пустым"
    
    if len(comment) < 10:
        return False, "❌ Комментарий слишком короткий (минимум 10 символов)"
    
    if len(comment) > 1000:
        return False, "❌ Комментарий слишком длинный (максимум 1000 символов)"
    
    # Проверка на спам (повторяющиеся символы)
    if re.search(r'(.)\1{10,}', comment):
        return False, "❌ Обнаружен спам"
    
    return True, None


def sanitize_text(text: str) -> str:
    """
    Очищает текст от потенциально опасных символов.
    
    Args:
        text: Исходный текст
        
    Returns:
        Безопасный текст
    """
    # Удаляем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
