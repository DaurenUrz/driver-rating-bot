# 🚀 Инструкция по деплою (развертыванию)

У вас есть 3 основных способа запустить бота 24/7. Выберите тот, который вам удобнее.

## 🏆 Вариант 1: Docker (Рекомендуемый)

Это самый надежный и простой способ. Бот и база данных запускаются в изолированных контейнерах одной командой.

### Предварительные требования
У вас должен быть установлен [Docker](https://docs.docker.com/get-docker/) и [Docker Compose](https://docs.docker.com/compose/install/).

### Шаги:

1. **Отредактируйте .env для Docker**
   
   Вам нужно изменить `DATABASE_URL` в `.env` файле, чтобы бот мог найти базу данных внутри Docker сети:
   ```env
   # Значения должны совпадать с теми, что в docker-compose.yml
   DATABASE_URL=postgresql://postgres:password@db:5432/driver_rating_db
   ```
   > **Важно:** Вместо `localhost` мы используем `db` (имя сервиса базы данных).

2. **Запустите контейнеры**
   ```bash
   docker-compose up -d --build
   ```
   Флаг `-d` запускает в фоновом режиме.

3. **Проверка работы**
   Посмотреть логи:
   ```bash
   docker-compose logs -f
   ```
   Остановить:
   ```bash
   docker-compose down
   ```

---

## ☁️ Вариант 2: Railway (Без сервера)

[Railway](https://railway.app/) — это облачная платформа, которая позволяет запустить бота без настройки серверов. У них есть бесплатный тариф (trial), но для стабильной работы лучше привязать карту (оплата только за ресурсы, ~$5/мес).

### Шаги:

1. Зарегистрируйтесь на [railway.app](https://railway.app/).
2. Нажмите **New Project** → **Provision PostgreSQL**. Это создаст базу данных.
3. Нажмите **New** → **GitHub Repo** и выберите репозиторий с вашим ботом.
4. Перейдите в настройки проекта (блок с ботом) → **Variables**.
5. Добавьте все переменные из вашего `.env`:
   - `BOT_TOKEN`
   - `ADMIN_ID`
   - `DATABASE_URL` (скопируйте из вкладки *Connect* вашей базы данных в Railway. Обычно она называется `DATABASE_URL`).
6. Railway автоматически обнаружит `requirements.txt` и запустит бота командой `python bot.py`.

---

## 🖥 Вариант 3: VPS + Systemd (Классический)

Если вы арендовали VPS сервер (Ubuntu/Debian), вы можете запустить бота как системную службу.

1. **Подключитесь к серверу**
   ```bash
   ssh root@your_server_ip
   ```

2. **Установите ПО**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv postgresql git
   ```

3. **Скачайте проект**
   ```bash
   git clone https://github.com/ваш-username/driver-rating-bot.git
   cd driver-rating-bot
   ```

4. **Настройте окружение**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   nano .env # Заполните данные
   ```

5. **Настройте базу данных**
   ```bash
   # Заходим под пользователем postgres
   sudo -u postgres psql
   
   # В консоли postgres:
   postgres=# CREATE DATABASE driver_rating_db;
   postgres=# CREATE USER myuser WITH ENCRYPTED PASSWORD 'mypassword';
   postgres=# GRANT ALL PRIVILEGES ON DATABASE driver_rating_db TO myuser;
   postgres=# \q
   ```
   *Не забудьте обновить `DATABASE_URL` в `.env`!*

6. **Создайте службу Systemd**
   
   ```bash
   sudo nano /etc/systemd/system/bot.service
   ```

   Вставьте следующий конфиг (поменяйте пути на свои!):
   ```ini
   [Unit]
   Description=Telegram Bot Service
   After=network.target postgresql.service

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/driver-rating-bot
   Environment="PATH=/root/driver-rating-bot/venv/bin"
   ExecStart=/root/driver-rating-bot/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

7. **Запустите службу**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable bot
   sudo systemctl start bot
   sudo systemctl status bot
   ```

---

## ⚠️ Важные советы после деплоя

1. **Не забудьте PROD-режим:** В `config.py` или `.env` убедитесь, что включены безопасные настройки (хотя у нас уже все через env).
2. **Бэкапы:** Регулярно делайте бэкап базы данных.
   Пример для Docker:
   ```bash
   docker exec -t driver_rating_db pg_dumpall -c -U postgres > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql
   ```
3. **Логи:** Следите за файлом `logs/bot.log` или выводом `docker logs`.
