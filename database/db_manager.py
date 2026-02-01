"""
Менеджер базы данных с пулом соединений и безопасными запросами.
"""
import asyncpg
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from config import config
from utils.logger import logger


class DatabaseManager:
    """Менеджер для работы с PostgreSQL базой данных"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init_pool(self):
        """Инициализирует пул соединений"""
        try:
            self.pool = await asyncpg.create_pool(
                config.DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("✅ Пул соединений с БД создан")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise
    
    async def close_pool(self):
        """Закрывает пул соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Пул соединений закрыт")
    
    @asynccontextmanager
    async def acquire(self):
        """Контекстный менеджер для получения соединения из пула"""
        async with self.pool.acquire() as conn:
            yield conn
    
    async def init_tables(self):
        """Создает таблицы если их нет"""
        async with self.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    referral_code TEXT UNIQUE,
                    referred_by BIGINT,
                    is_banned BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Таблица отзывов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    plate TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT NOT NULL,
                    photo_id TEXT,
                    video_id TEXT,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Индексы для быстрого поиска
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_plate ON reviews(plate) WHERE is_deleted = FALSE')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id)')
            
            # Таблица подписок на авто
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    user_id BIGINT NOT NULL,
                    plate TEXT NOT NULL,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, plate),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица подписок (платных)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    user_id BIGINT PRIMARY KEY,
                    tier TEXT NOT NULL DEFAULT 'free',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    auto_renew BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица транзакций
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    payment_id TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица реферальной программы
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL,
                    bonus_granted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (referrer_id, referred_id),
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица использования (для лимитов)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    user_id BIGINT NOT NULL,
                    date DATE NOT NULL,
                    searches INTEGER DEFAULT 0,
                    reviews INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            logger.info("✅ Таблицы БД инициализированы")
    
    # --- ПОЛЬЗОВАТЕЛИ ---
    
    async def create_or_update_user(self, user_id: int, username: str, full_name: str) -> None:
        """Создает или обновляет пользователя"""
        async with self.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, full_name, last_active)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE
                SET username = $2, full_name = $3, last_active = CURRENT_TIMESTAMP
            ''', user_id, username, full_name)
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе"""
        async with self.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
            return dict(row) if row else None
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверяет, забанен ли пользователь"""
        async with self.acquire() as conn:
            result = await conn.fetchval(
                'SELECT is_banned FROM users WHERE user_id = $1',
                user_id
            )
            return result or False
    
    # --- ОТЗЫВЫ ---
    
    async def create_review(
        self,
        plate: str,
        rating: int,
        comment: str,
        user_id: int,
        photo_id: Optional[str] = None,
        video_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> int:
        """Создает новый отзыв и возвращает его ID"""
        async with self.acquire() as conn:
            review_id = await conn.fetchval('''
                INSERT INTO reviews (plate, rating, comment, user_id, photo_id, video_id, latitude, longitude)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            ''', plate, rating, comment, user_id, photo_id, video_id, latitude, longitude)
            
            logger.info(f"✅ Создан отзыв #{review_id} для {plate} от пользователя {user_id}")
            return review_id
    
    async def get_reviews_by_plate(self, plate: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает все отзывы по номеру с информацией об авторе"""
        async with self.acquire() as conn:
            query = '''
                SELECT r.*, u.full_name as author_name, u.username as author_username
                FROM reviews r
                LEFT JOIN users u ON r.user_id = u.user_id
                WHERE r.plate = $1 AND r.is_deleted = FALSE
                ORDER BY r.created_at DESC
            '''
            if limit:
                query += f' LIMIT {limit}'
            
            rows = await conn.fetch(query, plate)
            return [dict(row) for row in rows]
    
    async def get_review_stats(self, plate: str) -> Dict[str, Any]:
        """Получает статистику по номеру"""
        async with self.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT
                    COUNT(*) as review_count,
                    AVG(rating) as avg_rating,
                    MAX(created_at) as last_review_date
                FROM reviews
                WHERE plate = $1 AND is_deleted = FALSE
            ''', plate)
            
            return dict(stats) if stats else {'review_count': 0, 'avg_rating': 0, 'last_review_date': None}
    
    async def delete_reviews_by_plate(self, plate: str) -> int:
        """Мягкое удаление всех отзывов по номеру"""
        async with self.acquire() as conn:
            count = await conn.fetchval('''
                UPDATE reviews SET is_deleted = TRUE
                WHERE plate = $1 AND is_deleted = FALSE
                RETURNING COUNT(*)
            ''', plate)
            
            logger.warning(f"🗑 Удалено {count} отзывов для номера {plate}")
            return count or 0
    
    # --- ПОДПИСКИ НА АВТО ---
    
    async def subscribe_to_plate(self, user_id: int, plate: str) -> bool:
        """Подписывает пользователя на уведомления по номеру"""
        async with self.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO subscriptions (user_id, plate)
                    VALUES ($1, $2)
                ''', user_id, plate)
                logger.info(f"✅ Пользователь {user_id} подписан на {plate}")
                return True
            except asyncpg.UniqueViolationError:
                return False
    
    async def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает список подписок пользователя"""
        async with self.acquire() as conn:
            rows = await conn.fetch('''
                SELECT s.plate, s.subscribed_at,
                       (SELECT COUNT(*) FROM reviews WHERE plate = s.plate AND is_deleted = FALSE) as review_count
                FROM subscriptions s
                WHERE s.user_id = $1
                ORDER BY s.subscribed_at DESC
            ''', user_id)
            
            return [dict(row) for row in rows]
    
    async def get_plate_subscribers(self, plate: str) -> List[int]:
        """Получает список пользователей, подписанных на номер"""
        async with self.acquire() as conn:
            rows = await conn.fetch(
                'SELECT user_id FROM subscriptions WHERE plate = $1',
                plate
            )
            return [row['user_id'] for row in rows]
    
    # --- ПЛАТНЫЕ ПОДПИСКИ ---
    
    async def get_user_subscription_tier(self, user_id: int) -> str:
        """Получает уровень подписки пользователя"""
        async with self.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT tier, expires_at FROM user_subscriptions
                WHERE user_id = $1
            ''', user_id)
            
            if not row:
                return 'free'
            
            # Проверяем, не истекла ли подписка
            if row['expires_at'] and row['expires_at'] < datetime.now():
                return 'free'
            
            return row['tier']
    
    async def set_user_subscription(self, user_id: int, tier: str, duration_days: int = 30) -> None:
        """Устанавливает подписку пользователю"""
        async with self.acquire() as conn:
            expires_at = datetime.now() + timedelta(days=duration_days)
            
            await conn.execute('''
                INSERT INTO user_subscriptions (user_id, tier, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET tier = $2, expires_at = $3, started_at = CURRENT_TIMESTAMP
            ''', user_id, tier, expires_at)
            
            logger.info(f"💎 Пользователю {user_id} установлена подписка {tier} до {expires_at}")
    
    # --- ЛИМИТЫ ИСПОЛЬЗОВАНИЯ ---
    
    async def increment_usage(self, user_id: int, action: str) -> int:
        """Увеличивает счетчик использования и возвращает текущее значение"""
        async with self.acquire() as conn:
            today = datetime.now().date()
            
            if action == 'search':
                column = 'searches'
            elif action == 'review':
                column = 'reviews'
            else:
                return 0
            
            await conn.execute(f'''
                INSERT INTO usage_stats (user_id, date, {column})
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, date) DO UPDATE
                SET {column} = usage_stats.{column} + 1
            ''', user_id, today)
            
            count = await conn.fetchval(f'''
                SELECT {column} FROM usage_stats
                WHERE user_id = $1 AND date = $2
            ''', user_id, today)
            
            return count or 0
    
    async def get_daily_usage(self, user_id: int) -> Dict[str, int]:
        """Получает статистику использования за сегодня"""
        async with self.acquire() as conn:
            today = datetime.now().date()
            row = await conn.fetchrow('''
                SELECT searches, reviews FROM usage_stats
                WHERE user_id = $1 AND date = $2
            ''', user_id, today)
            
            if row:
                return {'searches': row['searches'], 'reviews': row['reviews']}
            return {'searches': 0, 'reviews': 0}
    
    # --- СТАТИСТИКА ДЛЯ АДМИНА ---
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Получает общую статистику для админа"""
        async with self.acquire() as conn:
            stats = {}
            
            # Всего пользователей
            stats['total_users'] = await conn.fetchval('SELECT COUNT(*) FROM users')
            
            # Всего отзывов
            stats['total_reviews'] = await conn.fetchval('SELECT COUNT(*) FROM reviews WHERE is_deleted = FALSE')
            
            # Уникальных номеров
            stats['unique_plates'] = await conn.fetchval('SELECT COUNT(DISTINCT plate) FROM reviews WHERE is_deleted = FALSE')
            
            # Активных подписок
            stats['active_subs'] = await conn.fetchval('''
                SELECT COUNT(*) FROM user_subscriptions
                WHERE tier != 'free' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ''')
            
            # Доход за месяц (примерный расчет)
            stats['monthly_revenue'] = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0) FROM transactions
                WHERE status = 'confirmed' AND created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            ''')
            
            # Новых пользователей за неделю
            stats['new_users_week'] = await conn.fetchval('''
                SELECT COUNT(*) FROM users
                WHERE joined_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
            ''')
            
            return stats


# Глобальный экземпляр менеджера БД
db = DatabaseManager()
