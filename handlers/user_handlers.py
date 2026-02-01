"""
Обработчики пользовательских команд.
"""
import uuid
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db_manager import db
from utils.validators import clean_plate, validate_plate, validate_comment, validate_rating
from utils.formatters import (
    format_review_header, format_single_review, format_car_list,
    format_subscription_info, format_user_stats
)
from utils.logger import logger
from config import config
from models.subscription_tiers import get_tier, can_perform_action
from keyboards.inline_keyboards import (
    get_rating_keyboard, get_share_keyboard, get_unlock_keyboard,
    get_subscription_tiers_keyboard, get_my_cars_keyboard
)
from keyboards.reply_keyboards import (
    get_main_menu_keyboard, get_location_keyboard, get_skip_keyboard
)

router = Router()


# --- СОСТОЯНИЯ ---
class ReviewForm(StatesGroup):
    entering_plate = State()
    choosing_rating = State()
    writing_comment = State()
    sending_location = State()
    sending_media = State()


class SearchForm(StatesGroup):
    entering_plate = State()


class GarageForm(StatesGroup):
    adding_plate = State()


# --- КОМАНДА /start ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    # Сохраняем/обновляем пользователя
    await db.create_or_update_user(user_id, username, full_name)
    
    # Проверяем реферальный код в deep link
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referral_code = args[1]
        # TODO: Обработка реферальной ссылки
        logger.info(f"Пользователь {user_id} пришел по реферальной ссылке: {referral_code}")
    
    # Отправляем приветствие
    welcome_text = (
        f"🇰🇿 <b>Driver Rating KZ</b>\n\n"
        f"Салам, {message.from_user.first_name}!\n\n"
        f"🔍 Проверяйте водителей по госномеру\n"
        f"✍️ Делитесь своим опытом\n"
        f"🚗 Следите за отзывами на свои авто\n\n"
        f"Бот полностью бесплатный! 🎉"
    )
    
    keyboard = get_main_menu_keyboard()
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
    
    logger.info(f"Пользователь {user_id} ({username}) запустил бота")


# --- ПОИСК ПО НОМЕРУ ---
@router.message(F.text == "🔍 Проверить номер")
@router.message(Command("search"))
async def search_start(message: Message, state: FSMContext):
    """Начало поиска по номеру"""
    user_id = message.from_user.id
    
    # Проверяем лимиты
    tier_name = await db.get_user_subscription_tier(user_id)
    usage = await db.get_daily_usage(user_id)
    
    can_search, error_msg = can_perform_action(tier_name, 'search', usage['searches'])
    
    if not can_search:
        await message.answer(error_msg, reply_markup=get_subscription_tiers_keyboard(), parse_mode="HTML")
        return
    
    await message.answer(
        "🔍 <b>Проверка номера</b>\n\n"
        "Введите госномер для поиска:\n"
        "<i>Например: 777ABC01</i>",
        parse_mode="HTML"
    )
    await state.set_state(SearchForm.entering_plate)


@router.message(SearchForm.entering_plate)
async def search_process(message: Message, state: FSMContext):
    """Обработка поиска"""
    # Проверяем, не нажал ли пользователь кнопку меню вместо ввода номера
    menu_buttons = ["🔍 Проверить номер", "✍️ Оставить отзыв", "🚗 Мой гараж", 
                    "💬 Поддержка", "🎁 Пригласить друга", "⏭ Пропустить", "❌ Отменить"]
    if message.text in menu_buttons:
        await state.clear()
        # Перенаправляем на соответствующий обработчик
        if message.text == "🔍 Проверить номер":
            return await search_start(message, state)
        elif message.text == "✍️ Оставить отзыв":
            return await review_start(message, state)
        elif message.text == "🚗 Мой гараж":
            return await my_garage(message)
        elif message.text == "💬 Поддержка":
            return await support_handler(message)
        elif message.text == "🎁 Пригласить друга":
            return await invite_friend(message)
        else:
            return
    
    user_id = message.from_user.id
    plate = clean_plate(message.text)
    
    # Валидация номера
    is_valid, error_msg = validate_plate(plate)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    # Увеличиваем счетчик поисков
    await db.increment_usage(user_id, 'search')
    
    # Получаем отзывы
    reviews = await db.get_reviews_by_plate(plate)
    stats = await db.get_review_stats(plate)
    
    if not reviews:
        region = config.get_region_name(plate)
        await message.answer(
            f"🚗 <b>{plate}</b> ({region})\n\n"
            f"📝 По этому номеру пока нет отзывов.\n\n"
            f"✍️ Будьте первым, кто оставит отзыв!",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Формируем заголовок
    region = config.get_region_name(plate)
    avg_rating = stats['avg_rating']
    review_count = stats['review_count']
    
    header = format_review_header(plate, region, avg_rating, review_count)
    await message.answer(header, reply_markup=get_share_keyboard(plate), parse_mode="HTML")
    
    # Проверяем, может ли пользователь видеть все отзывы
    tier_name = await db.get_user_subscription_tier(user_id)
    can_view_all, _ = can_perform_action(tier_name, 'view_all_reviews')
    
    # Показываем отзывы
    for i, review in enumerate(reviews, 1):
        # Если не премиум и это не первый отзыв - показываем заглушку
        if i > 1 and not can_view_all:
            hidden_count = len(reviews) - 1
            await message.answer(
                f"🔒 <b>Скрыто еще {hidden_count} отзыв(ов)</b>\n\n"
                f"Оформите подписку для просмотра всех отзывов!",
                reply_markup=get_unlock_keyboard(),
                parse_mode="HTML"
            )
            break
        
        # Форматируем отзыв
        has_media = bool(review['photo_id'] or review['video_id'])
        author_name = review.get('author_name') or review.get('author_username') or 'Аноним'
        caption = format_single_review(i, review['rating'], review['comment'], has_media, author_name)
        
        # Клавиатура с геолокацией если есть
        keyboard = None
        if review['latitude'] and review['longitude']:
            from keyboards.inline_keyboards import get_location_map_keyboard
            keyboard = get_location_map_keyboard(review['latitude'], review['longitude'])
        
        # Отправляем медиа или текст
        if review['video_id']:
            await message.answer_video(
                review['video_id'],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif review['photo_id']:
            await message.answer_photo(
                review['photo_id'],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
    
    await state.clear()
    logger.info(f"Пользователь {user_id} проверил номер {plate}")


# --- ОСТАВИТЬ ОТЗЫВ ---
@router.message(F.text == "✍️ Оставить отзыв")
@router.message(Command("review"))
async def review_start(message: Message, state: FSMContext):
    """Начало создания отзыва"""
    user_id = message.from_user.id
    
    # Проверяем, не забанен ли пользователь
    if await db.is_user_banned(user_id):
        await message.answer("❌ Вы заблокированы и не можете оставлять отзывы.")
        return
    
    # Проверяем лимиты
    usage = await db.get_daily_usage(user_id)
    if usage['reviews'] >= config.MAX_REVIEWS_PER_DAY:
        await message.answer(
            f"❌ Вы достигли дневного лимита отзывов ({config.MAX_REVIEWS_PER_DAY})\n\n"
            f"Попробуйте завтра!"
        )
        return
    
    await message.answer(
        "✍️ <b>Новый отзыв</b>\n\n"
        "Введите госномер автомобиля:\n"
        "<i>Например: 777ABC01</i>",
        parse_mode="HTML"
    )
    await state.set_state(ReviewForm.entering_plate)


@router.message(ReviewForm.entering_plate)
async def review_plate(message: Message, state: FSMContext):
    """Получение номера для отзыва"""
    # Проверяем, не нажал ли пользователь кнопку меню
    menu_buttons = ["🔍 Проверить номер", "✍️ Оставить отзыв", "🚗 Мой гараж", 
                    "💬 Поддержка", "🎁 Пригласить друга", "⏭ Пропустить", "❌ Отменить"]
    if message.text in menu_buttons:
        await state.clear()
        if message.text == "🔍 Проверить номер":
            return await search_start(message, state)
        elif message.text == "✍️ Оставить отзыв":
            return await review_start(message, state)
        elif message.text == "🚗 Мой гараж":
            return await my_garage(message)
        elif message.text == "💬 Поддержка":
            return await support_handler(message)
        elif message.text == "🎁 Пригласить друга":
            return await invite_friend(message)
        else:
            return
    
    plate = clean_plate(message.text)
    
    # Валидация
    is_valid, error_msg = validate_plate(plate)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(plate=plate)
    
    region = config.get_region_name(plate)
    await message.answer(
        f"🚗 <b>{plate}</b> ({region})\n\n"
        f"Оцените водителя:",
        reply_markup=get_rating_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ReviewForm.choosing_rating)


@router.callback_query(F.data.startswith("rate_"), ReviewForm.choosing_rating)
async def review_rating(callback: CallbackQuery, state: FSMContext):
    """Получение оценки"""
    rating = int(callback.data.split("_")[1])
    
    if not validate_rating(rating):
        await callback.answer("❌ Неверная оценка")
        return
    
    await state.update_data(rating=rating)
    
    await callback.message.answer(
        f"{'⭐' * rating}\n\n"
        f"Напишите комментарий:\n"
        f"<i>(минимум 10 символов)</i>",
        parse_mode="HTML"
    )
    await state.set_state(ReviewForm.writing_comment)
    await callback.answer()


@router.message(ReviewForm.writing_comment)
async def review_comment(message: Message, state: FSMContext):
    """Получение комментария"""
    # Проверяем, не нажал ли пользователь кнопку меню
    menu_buttons = ["🔍 Проверить номер", "✍️ Оставить отзыв", "🚗 Мой гараж", 
                    "💬 Поддержка", "🎁 Пригласить друга", "⏭ Пропустить", "❌ Отменить"]
    if message.text in menu_buttons:
        await state.clear()
        if message.text == "🔍 Проверить номер":
            return await search_start(message, state)
        elif message.text == "✍️ Оставить отзыв":
            return await review_start(message, state)
        elif message.text == "🚗 Мой гараж":
            return await my_garage(message)
        elif message.text == "💬 Поддержка":
            return await support_handler(message)
        elif message.text == "🎁 Пригласить друга":
            return await invite_friend(message)
        else:
            return
    
    comment = message.text
    
    # Валидация
    is_valid, error_msg = validate_comment(comment)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(comment=comment)
    
    await message.answer(
        "📍 Где это произошло?\n\n"
        "Отправьте геолокацию или пропустите этот шаг:",
        reply_markup=get_location_keyboard()
    )
    await state.set_state(ReviewForm.sending_location)


@router.message(ReviewForm.sending_location, F.location)
async def review_location(message: Message, state: FSMContext):
    """Получение геолокации"""
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )
    
    await message.answer(
        "📸 Добавьте фото или видео (необязательно):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ReviewForm.sending_media)


@router.message(ReviewForm.sending_location, F.text == "⏭ Пропустить")
async def review_skip_location(message: Message, state: FSMContext):
    """Пропуск геолокации"""
    await message.answer(
        "📸 Добавьте фото или видео (необязательно):",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ReviewForm.sending_media)


@router.message(ReviewForm.sending_media)
async def review_finish(message: Message, state: FSMContext):
    """Завершение создания отзыва"""
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Получаем медиа если есть
    photo_id = message.photo[-1].file_id if message.photo else None
    video_id = message.video.file_id if message.video else None
    
    # Сохраняем отзыв
    review_id = await db.create_review(
        plate=data['plate'],
        rating=data['rating'],
        comment=data['comment'],
        user_id=user_id,
        photo_id=photo_id,
        video_id=video_id,
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    # Увеличиваем счетчик
    await db.increment_usage(user_id, 'review')
    
    # Уведомляем подписчиков
    subscribers = await db.get_plate_subscribers(data['plate'])
    for subscriber_id in subscribers:
        if subscriber_id != user_id:  # Не уведомляем самого себя
            try:
                from aiogram import Bot
                from config import config as cfg
                bot = Bot(token=cfg.BOT_TOKEN)
                await bot.send_message(
                    subscriber_id,
                    f"🔔 <b>Новый отзыв на ваш автомобиль!</b>\n\n"
                    f"🚗 Номер: <code>{data['plate']}</code>\n"
                    f"⭐ Оценка: {'⭐' * data['rating']}\n\n"
                    f"Проверьте детали в разделе 'Мой гараж'",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить пользователя {subscriber_id}: {e}")
    
    await message.answer(
        "✅ <b>Отзыв опубликован!</b>\n\n"
        "Спасибо за вклад в безопасность на дорогах! 🙏",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    await state.clear()
    logger.info(f"Пользователь {user_id} оставил отзыв #{review_id} на номер {data['plate']}")


# --- МОЙ ГАРАЖ ---
@router.message(F.text == "🚗 Мой гараж")
@router.message(Command("my_cars"))
async def my_garage(message: Message):
    """Показывает автомобили пользователя"""
    user_id = message.from_user.id
    
    cars = await db.get_user_subscriptions(user_id)
    
    if not cars:
        await message.answer(
            "🚗 <b>Ваш гараж пуст</b>\n\n"
            "Добавьте свой автомобиль, чтобы получать уведомления о новых отзывах!",
            reply_markup=get_my_cars_keyboard([]),
            parse_mode="HTML"
        )
    else:
        # Форматируем список
        car_data = []
        for car in cars:
            region = config.get_region_name(car['plate'])
            car_data.append({
                'plate': car['plate'],
                'region': region,
                'review_count': car['review_count']
            })
        
        text = format_car_list(car_data)
        plates = [car['plate'] for car in cars]
        
        await message.answer(
            text,
            reply_markup=get_my_cars_keyboard(plates),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "add_car")
async def add_car_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления авто"""
    user_id = callback.from_user.id
    
    # Проверяем лимиты
    tier_name = await db.get_user_subscription_tier(user_id)
    current_cars = await db.get_user_subscriptions(user_id)
    
    can_add, error_msg = can_perform_action(tier_name, 'add_car', len(current_cars))
    
    if not can_add:
        await callback.message.answer(
            error_msg,
            reply_markup=get_subscription_tiers_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.answer(
        "🚗 <b>Добавление автомобиля</b>\n\n"
        "Введите госномер:",
        parse_mode="HTML"
    )
    await state.set_state(GarageForm.adding_plate)
    await callback.answer()


@router.message(GarageForm.adding_plate)
async def add_car_finish(message: Message, state: FSMContext):
    """Завершение добавления авто"""
    # Проверяем, не нажал ли пользователь кнопку меню
    menu_buttons = ["🔍 Проверить номер", "✍️ Оставить отзыв", "🚗 Мой гараж", 
                    "💬 Поддержка", "🎁 Пригласить друга", "⏭ Пропустить", "❌ Отменить"]
    if message.text in menu_buttons:
        await state.clear()
        if message.text == "🔍 Проверить номер":
            return await search_start(message, state)
        elif message.text == "✍️ Оставить отзыв":
            return await review_start(message, state)
        elif message.text == "🚗 Мой гараж":
            return await my_garage(message)
        elif message.text == "💬 Поддержка":
            return await support_handler(message)
        elif message.text == "🎁 Пригласить друга":
            return await invite_friend(message)
        else:
            return
    
    user_id = message.from_user.id
    plate = clean_plate(message.text)
    
    # Валидация
    is_valid, error_msg = validate_plate(plate)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    # Добавляем в гараж
    success = await db.subscribe_to_plate(user_id, plate)
    
    if success:
        region = config.get_region_name(plate)
        await message.answer(
            f"✅ <b>Автомобиль добавлен!</b>\n\n"
            f"🚗 {plate} ({region})\n\n"
            f"Теперь вы будете получать уведомления о новых отзывах.",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Этот автомобиль уже есть в вашем гараже.")
    
    await state.clear()


@router.callback_query(F.data.startswith("remove_car_"))
async def remove_car(callback: CallbackQuery):
    """Удаление авто из гаража"""
    plate = callback.data.replace("remove_car_", "")
    user_id = callback.from_user.id
    
    # TODO: Добавить метод удаления в db_manager
    await callback.answer("🗑 Автомобиль удален из гаража")
    
    # Обновляем список
    await my_garage(callback.message)


# --- ПОДЕЛИТЬСЯ ---
@router.callback_query(F.data.startswith("share_"))
async def share_plate(callback: CallbackQuery):
    """Генерирует карточку для шаринга"""
    plate = callback.data.replace("share_", "")
    
    stats = await db.get_review_stats(plate)
    
    if stats['review_count'] == 0:
        await callback.answer("Нет отзывов для шаринга")
        return
    
    avg_rating = stats['avg_rating']
    region = config.get_region_name(plate)
    
    share_text = (
        f"🚗 <b>DRIVER CARD: {plate}</b>\n"
        f"📍 {region}\n"
        f"📊 Рейтинг: {'⭐' * int(round(avg_rating))} ({avg_rating:.1f}/5)\n"
        f"💬 Отзывов: {stats['review_count']}\n\n"
        f"👉 Проверено в @DriverRatingKZ_bot"
    )
    
    await callback.message.answer(
        "📸 <b>Сделайте скриншот этой карточки:</b>\n\n" + share_text,
        parse_mode="HTML"
    )
    await callback.answer()


# --- ПОДДЕРЖКА ---
@router.message(F.text == "💬 Поддержка")
async def support_handler(message: Message):
    """Показывает информацию о поддержке"""
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Если у вас есть вопросы, предложения или вы нашли баг — напишите нам!\n\n"
        "📩 Telegram: @urzknvv\n\n"
        "Мы стараемся отвечать как можно быстрее 🙏",
        parse_mode="HTML"
    )


# --- ПРИГЛАСИТЬ ДРУГА ---
@router.message(F.text == "🎁 Пригласить друга")
async def invite_friend(message: Message):
    """Генерирует реферальную ссылку"""
    user_id = message.from_user.id
    
    # Создаем реферальную ссылку
    bot_username = "DriverRatingKZ_bot"
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    await message.answer(
        "🚗 <b>Знаешь крутой бот? Расскажи друзьям!</b>\n\n"
        f"<code>{referral_link}</code>\n\n"
        "Отправь ссылку 👇",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📲 Поделиться",
                url=f"https://t.me/share/url?url={referral_link}&text=Проверяй водителей по госномеру!"
            )]
        ])
    )
    
    logger.info(f"Пользователь {user_id} запросил реферальную ссылку")


# --- ПРОСМОТР АВТО ИЗ ГАРАЖА ---
@router.callback_query(F.data.startswith("view_car_"))
async def view_car_reviews(callback: CallbackQuery):
    """Показывает все отзывы на авто из гаража"""
    plate = callback.data.replace("view_car_", "")
    
    # Получаем отзывы
    reviews = await db.get_reviews_by_plate(plate)
    stats = await db.get_review_stats(plate)
    
    if not reviews:
        region = config.get_region_name(plate)
        await callback.message.answer(
            f"🚗 <b>{plate}</b> ({region})\n\n"
            f"📝 По этому номеру пока нет отзывов.",
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Формируем заголовок
    region = config.get_region_name(plate)
    avg_rating = stats['avg_rating']
    review_count = stats['review_count']
    
    header = format_review_header(plate, region, avg_rating, review_count)
    await callback.message.answer(header, reply_markup=get_share_keyboard(plate), parse_mode="HTML")
    
    # Показываем все отзывы
    for i, review in enumerate(reviews, 1):
        has_media = bool(review['photo_id'] or review['video_id'])
        author_name = review.get('author_name') or review.get('author_username') or 'Аноним'
        caption = format_single_review(i, review['rating'], review['comment'], has_media, author_name)
        
        # Клавиатура с геолокацией если есть
        keyboard = None
        if review['latitude'] and review['longitude']:
            from keyboards.inline_keyboards import get_location_map_keyboard
            keyboard = get_location_map_keyboard(review['latitude'], review['longitude'])
        
        # Отправляем медиа или текст
        if review['video_id']:
            await callback.message.answer_video(
                review['video_id'],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif review['photo_id']:
            await callback.message.answer_photo(
                review['photo_id'],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()
    logger.info(f"Пользователь {callback.from_user.id} просмотрел отзывы на {plate} из гаража")
