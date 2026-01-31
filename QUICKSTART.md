# 🚀 Быстрый старт

## Шаг 1: Настройка окружения

```bash
# Перейдите в папку проекта
cd driver-rating-bot

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

## Шаг 2: Настройка .env файла

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте файл
nano .env
```

**Обязательно заполните:**
```env
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_ID=ваш_telegram_id
DATABASE_URL=postgresql://user:password@localhost:5432/driver_rating_db
```

## Шаг 3: Настройка PostgreSQL

### Вариант 1: Локальная установка

```bash
# Установите PostgreSQL (если еще не установлен)
# macOS:
brew install postgresql
brew services start postgresql

# Ubuntu/Debian:
sudo apt install postgresql
sudo systemctl start postgresql

# Создайте базу данных
createdb driver_rating_db

# Или через psql:
psql postgres
CREATE DATABASE driver_rating_db;
\q
```

### Вариант 2: Облачная БД (рекомендуется для продакшена)

Используйте сервисы:
- **Supabase** (бесплатный тариф)
- **ElephantSQL** (бесплатный тариф)
- **Railway** (бесплатный тариф)

Просто скопируйте Connection String в `DATABASE_URL`

## Шаг 4: Получите токен бота

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен в `.env`

## Шаг 5: Узнайте свой Telegram ID

1. Найдите [@userinfobot](https://t.me/userinfobot)
2. Отправьте `/start`
3. Скопируйте ваш ID в `.env`

## Шаг 6: Запустите бота

```bash
python bot.py
```

Вы должны увидеть:
```
✅ Пул соединений с БД создан
✅ Таблицы БД инициализированы
✅ Команды бота установлены
✅ Бот успешно запущен!
```

## Шаг 7: Протестируйте

1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Попробуйте основные функции

## 🔄 Миграция со старого бота

Если у вас уже есть данные в старой версии:

```bash
# Установите OLD_DATABASE_URL
export OLD_DATABASE_URL="postgresql://..."

# Запустите миграцию
python migrate_old_data.py
```

## ⚙️ Настройка для продакшена

### Systemd service (Linux)

```bash
sudo nano /etc/systemd/system/driver-rating-bot.service
```

```ini
[Unit]
Description=Driver Rating KZ Pro Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/driver-rating-bot
Environment="PATH=/path/to/driver-rating-bot/venv/bin"
ExecStart=/path/to/driver-rating-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable driver-rating-bot
sudo systemctl start driver-rating-bot
```

### Docker (опционально)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

```bash
docker build -t driver-rating-bot .
docker run -d --env-file .env driver-rating-bot
```

## 🎯 Следующие шаги

1. **Настройте платежи**: Укажите номер Kaspi в `.env`
2. **Протестируйте все функции**: Поиск, отзывы, подписки
3. **Настройте мониторинг**: Проверяйте логи в `logs/bot.log`
4. **Запустите рекламу**: Привлекайте первых пользователей
5. **Собирайте фидбек**: Улучшайте на основе отзывов

## 📞 Поддержка

Если что-то не работает:
1. Проверьте логи: `tail -f logs/bot.log`
2. Проверьте `.env` файл
3. Убедитесь что БД доступна
4. Проверьте токен бота

## 💡 Полезные команды

```bash
# Просмотр логов в реальном времени
tail -f logs/bot.log

# Проверка статуса (если используете systemd)
sudo systemctl status driver-rating-bot

# Перезапуск
sudo systemctl restart driver-rating-bot

# Просмотр логов systemd
sudo journalctl -u driver-rating-bot -f
```

Удачи! 🚀
