# Используем официальный легкий образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (нужны для сборки некоторых python пакетов)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код проекта
COPY . .

# Удаляем виртуальное окружение, если оно было скопировано (на всякий случай)
RUN rm -rf venv

# Команда запуска
CMD ["python", "bot.py"]
