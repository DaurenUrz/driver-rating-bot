"""
Модуль для работы с логированием.
Настраивает структурированное логирование с ротацией файлов.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import config


def setup_logger(name: str = "driver_rating_bot") -> logging.Logger:
    """
    Настраивает и возвращает логгер с форматированием и ротацией файлов.
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный вывод
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый вывод с ротацией (макс 10MB, 5 файлов)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / config.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Глобальный логгер
logger = setup_logger()
