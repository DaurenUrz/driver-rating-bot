"""
Скрипт миграции данных из старой версии бота в новую.

Использование:
    python migrate_old_data.py

Требования:
    - Старая БД должна быть доступна
    - Новая БД должна быть уже инициализирована (запустите bot.py один раз)
"""
import asyncio
import asyncpg
import os
from datetime import datetime

# URL старой базы данных (из вашего старого бота)
OLD_DATABASE_URL = os.getenv('OLD_DATABASE_URL', '')

# URL новой базы данных
NEW_DATABASE_URL = os.getenv('DATABASE_URL', '')


async def migrate_users():
    """Миграция пользователей"""
    old_conn = await asyncpg.connect(OLD_DATABASE_URL)
    new_conn = await asyncpg.connect(NEW_DATABASE_URL)
    
    print("📊 Миграция пользователей...")
    
    # Получаем пользователей из старой БД
    old_users = await old_conn.fetch('SELECT * FROM users')
    
    migrated = 0
    for user in old_users:
        try:
            await new_conn.execute('''
                INSERT INTO users (user_id, username, full_name, joined_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING
            ''', user['user_id'], user['username'], user['full_name'], 
                user.get('joined_at', datetime.now()))
            migrated += 1
        except Exception as e:
            print(f"❌ Ошибка миграции пользователя {user['user_id']}: {e}")
    
    await old_conn.close()
    await new_conn.close()
    
    print(f"✅ Мигрировано пользователей: {migrated}/{len(old_users)}")


async def migrate_reviews():
    """Миграция отзывов"""
    old_conn = await asyncpg.connect(OLD_DATABASE_URL)
    new_conn = await asyncpg.connect(NEW_DATABASE_URL)
    
    print("📊 Миграция отзывов...")
    
    # Получаем отзывы из старой БД
    old_reviews = await old_conn.fetch('SELECT * FROM reviews')
    
    migrated = 0
    for review in old_reviews:
        try:
            await new_conn.execute('''
                INSERT INTO reviews (plate, rating, comment, photo_id, video_id, 
                                   latitude, longitude, user_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', review['plate'], review['rating'], review['comment'],
                review.get('photo_id'), review.get('video_id'),
                review.get('latitude'), review.get('longitude'),
                review['user_id'], datetime.now())
            migrated += 1
        except Exception as e:
            print(f"❌ Ошибка миграции отзыва: {e}")
    
    await old_conn.close()
    await new_conn.close()
    
    print(f"✅ Мигрировано отзывов: {migrated}/{len(old_reviews)}")


async def migrate_subscriptions():
    """Миграция подписок на авто"""
    old_conn = await asyncpg.connect(OLD_DATABASE_URL)
    new_conn = await asyncpg.connect(NEW_DATABASE_URL)
    
    print("📊 Миграция подписок на авто...")
    
    # Получаем подписки из старой БД
    old_subs = await old_conn.fetch('SELECT * FROM subscriptions')
    
    migrated = 0
    for sub in old_subs:
        try:
            await new_conn.execute('''
                INSERT INTO subscriptions (user_id, plate)
                VALUES ($1, $2)
                ON CONFLICT (user_id, plate) DO NOTHING
            ''', sub['user_id'], sub['plate'])
            migrated += 1
        except Exception as e:
            print(f"❌ Ошибка миграции подписки: {e}")
    
    await old_conn.close()
    await new_conn.close()
    
    print(f"✅ Мигрировано подписок: {migrated}/{len(old_subs)}")


async def migrate_purchases():
    """Миграция покупок в новую систему подписок"""
    old_conn = await asyncpg.connect(OLD_DATABASE_URL)
    new_conn = await asyncpg.connect(NEW_DATABASE_URL)
    
    print("📊 Миграция покупок...")
    
    # Получаем покупки из старой БД
    old_purchases = await old_conn.fetch('SELECT * FROM purchases')
    
    migrated = 0
    for purchase in old_purchases:
        try:
            # Определяем уровень подписки
            if purchase.get('multi_car', 0) == 1:
                tier = 'premium'
            elif purchase.get('access_granted', 0) == 1:
                tier = 'basic'
            else:
                continue  # Пропускаем бесплатных
            
            # Устанавливаем подписку на 30 дней от текущей даты
            await new_conn.execute('''
                INSERT INTO user_subscriptions (user_id, tier, expires_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP + INTERVAL '30 days')
                ON CONFLICT (user_id) DO UPDATE
                SET tier = $2, expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days'
            ''', purchase['user_id'], tier)
            migrated += 1
        except Exception as e:
            print(f"❌ Ошибка миграции покупки: {e}")
    
    await old_conn.close()
    await new_conn.close()
    
    print(f"✅ Мигрировано покупок: {migrated}/{len(old_purchases)}")


async def main():
    """Главная функция миграции"""
    print("🚀 Начало миграции данных...\n")
    
    if not OLD_DATABASE_URL or not NEW_DATABASE_URL:
        print("❌ Ошибка: не указаны DATABASE_URL")
        print("Установите переменные окружения:")
        print("  OLD_DATABASE_URL - URL старой БД")
        print("  DATABASE_URL - URL новой БД")
        return
    
    try:
        # Миграция в правильном порядке (из-за внешних ключей)
        await migrate_users()
        print()
        await migrate_reviews()
        print()
        await migrate_subscriptions()
        print()
        await migrate_purchases()
        print()
        
        print("✅ Миграция завершена успешно!")
        print("\n⚠️  ВАЖНО: Проверьте данные в новой БД перед удалением старой!")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка миграции: {e}")


if __name__ == "__main__":
    asyncio.run(main())
