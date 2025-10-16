# Файл: bot.py

import logging
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

# Импортируем наши модули
from config import Config
import keyboards as kb
import google_sheets as gs
from database import (async_session, create_tables, users, orders, applications, viewed_orders,
                        select, update, delete, and_, insert)

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Инициализация бота и диспетчера ---
storage = MemoryStorage()
bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# --- FSM Состояния (машина состояний) ---

class Registration(StatesGroup):
    full_name = State()
    sphere = State()
    bio = State()
    portfolio = State()
    role = State()
    confirm_publication = State()

class OrderCreation(StatesGroup):
    title = State()
    description = State()
    photo = State()

class ProfileEditing(StatesGroup):
    field = State()
    new_value = State()

# --- Вспомогательные функции ---

async def get_user(user_id: int):
    """Получает пользователя из БД."""
    async with async_session() as session:
        result = await session.execute(select(users).where(users.c.user_id == user_id))
        return result.fetchone()

def format_user_profile(user_data) -> str:
    """Форматирует профиль пользователя в красивый текст."""
    role_map = {
        'worker': 'Исполнитель',
        'employer': 'Заказчик',
        'both': 'Исполнитель и Заказчик'
    }
    return (
        f"<b>👤 Имя:</b> {user_data.full_name}\n"
        f"<b>🛠️ Сфера:</b> {user_data.sphere}\n"
        f"<b>📝 О себе:</b> {user_data.bio}\n"
        f"<b>🔗 Портфолио:</b> {user_data.portfolio or '—'}\n"
        f"<b>🎯 Роль:</b> {role_map.get(user_data.role, 'Не указана')}\n"
        f"<b>✈️ TG:</b> @{user_data.username}"
    )

# --- Обработчики событий в группе ---

@dp.message(F.new_chat_members)
async def on_user_joined(message: types.Message):
    """Приветствует нового участника в общем чате группы."""
    for user in message.new_chat_members:
        if not user.is_bot:
            await message.answer(
                f"👋 Добро пожаловать в наше комьюнити, {user.full_name}!\n\n"
                f"Чтобы получить доступ ко всем возможностям (создание заказов, поиск работы), "
                f"нажми на мое имя и запусти меня в личных сообщениях командой /start"
                f"Создано @velja297"
            )
            logger.info(f"Приветствие для нового пользователя {user.id} в группе {message.chat.id}")


# --- РЕГИСТРАЦИЯ И СТАРТ ---

@dp.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start. Начинает регистрацию или показывает главное меню."""
    await state.clear()
    user = await get_user(message.from_user.id)
    if user:
        await message.answer("С возвращением! 👋", reply_markup=kb.get_main_menu_keyboard())
    else:
        await state.set_state(Registration.full_name)
        await message.answer(
            "👋 Добро пожаловать в Connect Bot! Создано @velja297\n\nДавайте создадим ваш профиль. "
            "Это поможет другим участникам узнать вас лучше.\n\n<b>Как вас зовут?</b>",
            reply_markup=types.ReplyKeyboardRemove()
        )

# ... (Остальные шаги регистрации)

@dp.message(Registration.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(Registration.sphere)
    await message.answer("🛠️ Отлично! Теперь укажите сферу вашей деятельности (например, 'UI/UX дизайн', 'Backend разработчик на Python').")

@dp.message(Registration.sphere)
async def process_sphere(message: types.Message, state: FSMContext):
    await state.update_data(sphere=message.text)
    await state.set_state(Registration.bio)
    await message.answer("📝 Расскажите немного о себе и своем опыте.")

@dp.message(Registration.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await state.set_state(Registration.portfolio)
    await message.answer("🔗 Отправьте ссылку на ваше портфолио (Behance, GitHub, личный сайт). Если его нет, отправьте прочерк '-'.")

@dp.message(Registration.portfolio)
async def process_portfolio(message: types.Message, state: FSMContext):
    await state.update_data(portfolio=message.text if message.text != '-' else None)
    await state.set_state(Registration.role)
    await message.answer("🎯 Выберите вашу основную роль:", reply_markup=kb.get_role_selection_keyboard())

@dp.message(Registration.role)
async def process_role(message: types.Message, state: FSMContext):
    role_map = {
        "Я ищу работу (Исполнитель)": "worker",
        "Я ищу исполнителя (Заказчик)": "employer",
        "И то, и другое": "both"
    }
    role = role_map.get(message.text)
    if not role:
        await message.answer("Пожалуйста, выберите роль с помощью кнопок.", reply_markup=kb.get_role_selection_keyboard())
        return

    await state.update_data(role=role)
    await state.set_state(Registration.confirm_publication)
    await message.answer(
        "🚀 Последний шаг! Опубликовать вашу анкету в общую группу для нетворкинга?",
        reply_markup=kb.get_confirm_publication_keyboard()
    )

@dp.message(Registration.confirm_publication)
async def process_final_registration(message: types.Message, state: FSMContext):
    """Завершает регистрацию, сохраняет пользователя в БД и Google Sheets."""
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    db_data = {
        'user_id': user_id,
        'username': message.from_user.username,
        'full_name': user_data['full_name'],
        'sphere': user_data['sphere'],
        'bio': user_data['bio'],
        'portfolio': user_data['portfolio'],
        'role': user_data['role'],
        'created_at': datetime.now()
    }

    async with async_session() as session:
        stmt = insert(users).values(db_data)
        await session.execute(stmt)
        await session.commit()
    
    logger.info(f"Пользователь {user_id} успешно зарегистрирован в БД.")
    await message.answer(
        "✅ Ваш профиль успешно создан! Добро пожаловать!",
        reply_markup=kb.get_main_menu_keyboard()
    )

    # Отправка в Google Sheets
    try:
        await gs.add_user_to_sheet(db_data)
    except Exception as e:
        logger.error(f"GSHEETS ОШИБКА (add_user): {e}")
        if Config.ADMIN_ID:
            await bot.send_message(Config.ADMIN_ID, f"⚠️ Не удалось добавить пользователя в Google Sheets.\n\nПользователь: {user_id}\nОшибка: {e}")

    # Публикация в группу
    if message.text == "Да, опубликовать":
        if Config.NETWORKING_GROUP_ID:
            try:
                new_user_profile = await get_user(user_id)
                profile_text = format_user_profile(new_user_profile)
                await bot.send_message( 
                    Config.NETWORKING_GROUP_ID,
                    f"👋 Встречайте нового участника!\n\n{profile_text}",
                    message_thread_id=Config.NETWORKING_TOPIC_ID    
                )
                logger.info(f"Анкета пользователя {user_id} опубликована в группе.")
            except Exception as e:
                logger.error(f"GROUP POST ОШИБКА (анкета): {e}")
                if Config.ADMIN_ID:
                    await bot.send_message(Config.ADMIN_ID, f"⚠️ Не удалось опубликовать анкету в группу.\n\nПользователь: {user_id}\nОшибка: {e}")
        else:
            logger.warning("NETWORKING_GROUP_ID не указан в конфиге.")

    await state.clear()


@dp.message(OrderCreation.photo)
async def process_order_photo(message: types.Message, state: FSMContext):
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    
    order_data = await state.get_data()
    employer = await get_user(message.from_user.id)

    db_data = {
        'employer_id': message.from_user.id,
        'title': order_data['title'],
        'description': order_data['description'],
        'photo_id': photo_id,
        'created_at': datetime.now()
    }

    async with async_session() as session:
        result = await session.execute(insert(orders).values(db_data).returning(orders.c.order_id))
        order_id = result.scalar_one()
        await session.commit()

    logger.info(f"Заказ {order_id} от пользователя {message.from_user.id} создан.")
    await message.answer(f"✅ Заказ «{order_data['title']}» успешно создан!", reply_markup=kb.get_main_menu_keyboard())

    # Отправка в Google Sheets
    db_data['order_id'] = order_id
    try:
        await gs.add_order_to_sheet(db_data, employer.username)
    except Exception as e:
        logger.error(f"GSHEETS ОШИБКА (add_order): {e}")
        if Config.ADMIN_ID:
            await bot.send_message(Config.ADMIN_ID, f"⚠️ Не удалось добавить заказ в Google Sheets.\n\nЗаказ: {order_id}\nОшибка: {e}")

    # Публикация в группу
    if Config.NETWORKING_GROUP_ID:
        try:
            order_text = (
                f"<b>🔥 Новый заказ: {db_data['title']}</b>\n\n"
                f"<b>📝 Описание:</b>\n{db_data['description']}\n\n"
                f"<b>Заказчик:</b> {employer.full_name} (@{employer.username})\n\n"
                f"<i>Откликнуться на заказ можно через бота в разделе 'Найти работу'.</i>"
            )
            if photo_id:
                await bot.send_photo(Config.NETWORKING_GROUP_ID, photo_id, caption=order_text,
                                     message_thread_id=Config.ORDERS_TOPIC_ID)
            else:
                await bot.send_message(Config.NETWORKING_GROUP_ID, order_text,
                                       message_thread_id=Config.ORDERS_TOPIC_ID)
            logger.info(f"Заказ {order_id} опубликован в группе.")
        except Exception as e:
            logger.error(f"GROUP POST ОШИБКА (заказ): {e}")
            if Config.ADMIN_ID:
                await bot.send_message(Config.ADMIN_ID, f"⚠️ Не удалось опубликовать заказ в группу.\n\nЗаказ: {order_id}\nОшибка: {e}")
    else:
        logger.warning("NETWORKING_GROUP_ID не указан в конфиге для публикации заказа.")

    await state.clear()

# --- ОСНОВНОЕ МЕНЮ ---

@dp.message(F.text == "👤 Мой профиль")
async def handle_my_profile(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Не удалось найти ваш профиль. Пожалуйста, пройдите регистрацию, нажав /start.")
        return

    profile_text = format_user_profile(user)
    visibility = "ВКЛ ✅ (виден в поиске)" if user.is_active else "ВЫКЛ ❌ (скрыт)"
    
    await message.answer(
        f"<b>Ваш профиль:</b>\n\n{profile_text}\n\n<b>Статус видимости:</b> {visibility}",
        reply_markup=kb.get_profile_keyboard()
    )


@dp.message(F.text == "🔍 Найти работу")
async def handle_find_job(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажмите /start.")
        return
    if user.role not in ['worker', 'both']:
        await message.answer("Ваша роль 'Заказчик' не позволяет искать работу. Вы можете изменить ее в профиле.")
        return

    await state.set_state("searching_jobs")
    await message.answer("Начинаю поиск актуальных заказов...")
    await show_next_order(message, state)


@dp.message(F.text == "📦 Мои заказы")
async def handle_my_orders(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(orders)
            .where(orders.c.employer_id == message.from_user.id)
            .order_by(orders.c.created_at.desc())
        )
        user_orders = result.fetchall()

    if not user_orders:
        await message.answer("У вас пока нет созданных заказов. Хотите создать первый?", reply_markup=kb.get_main_menu_keyboard())
        return

    await message.answer("<b>Ваши созданные заказы:</b>")
    for order in user_orders:
        status_icon = "🟢 (Открыт)" if order.status == 'open' else "🔒 (Закрыт)"
        text = (
            f"<b>Заказ #{order.order_id}: {order.title}</b>\n"
            f"Статус: {status_icon}\n"
            f"<i>Описание:</i> {order.description[:100]}..."
        )
        is_closed = order.status == 'closed'
        await message.answer(text, reply_markup=kb.get_order_management_keyboard(order.order_id, is_closed))


@dp.message(F.text == "➕ Создать заказ")
async def handle_create_order(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала нужно зарегистрироваться. Нажмите /start.")
        return
    if user.role not in ['employer', 'both']:
        await message.answer("Ваша роль 'Исполнитель' не позволяет создавать заказы. Вы можете изменить ее в профиле.")
        return
    
    await state.set_state(OrderCreation.title)
    await message.answer("Введите название для вашего заказа (например, 'Разработать логотип для кофейни').", reply_markup=types.ReplyKeyboardRemove())

# ... (Остальные шаги создания заказа)
@dp.message(OrderCreation.title)
async def process_order_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(OrderCreation.description)
    await message.answer("Отлично. Теперь подробно опишите задачу.")

@dp.message(OrderCreation.description)
async def process_order_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(OrderCreation.photo)
    await message.answer("Прикрепите фото или референс, если нужно. Если нет — отправьте прочерк '-'.")


# --- ПОИСК РАБОТЫ ---

async def show_next_order(message_or_call: types.Message | types.CallbackQuery, state: FSMContext):
    """Показывает следующий доступный заказ."""
    user_id = message_or_call.from_user.id
    message = message_or_call if isinstance(message_or_call, types.Message) else message_or_call.message

    async with async_session() as session:
        # Сначала получим ID заказов, которые пользователь уже видел в этой сессии
        viewed_result = await session.execute(
            select(viewed_orders.c.order_id).where(viewed_orders.c.viewer_id == user_id)
        )
        viewed_ids = [row[0] for row in viewed_result]

        # Ищем новый заказ
        time_limit = datetime.now() - timedelta(hours=Config.ORDER_LIFETIME_HOURS)
        query = (
            select(orders, users.c.full_name, users.c.username)
            .join(users, orders.c.employer_id == users.c.user_id)
            .where(
                and_(
                    orders.c.status == 'open',
                    orders.c.employer_id != user_id,
                    orders.c.created_at >= time_limit,
                    orders.c.order_id.notin_(viewed_ids)
                )
            )
            .order_by(orders.c.created_at.desc())
            .limit(1)
        )
        result = await session.execute(query)
        order = result.fetchone()

    if order:
        await state.update_data(current_order_id=order.order_id)
        # Отмечаем заказ как просмотренный
        async with async_session() as session:
            await session.execute(insert(viewed_orders).values(viewer_id=user_id, order_id=order.order_id))
            await session.commit()
        
        text = (
            f"<b>Заказ: {order.title}</b>\n\n"
            f"<b>Описание:</b>\n{order.description}\n\n"
            f"<b>Заказчик:</b> {order.full_name} (@{order.username})"
        )
        
        if order.photo_id:
            await message.answer_photo(order.photo_id, caption=text, reply_markup=kb.get_job_search_keyboard(order.order_id))
        else:
            await message.answer(text, reply_markup=kb.get_job_search_keyboard(order.order_id))
    else:
        # Если новых заказов нет, сбрасываем историю просмотров и пробуем еще раз
        async with async_session() as session:
            await session.execute(delete(viewed_orders).where(viewed_orders.c.viewer_id == user_id))
            await session.commit()
        
        # Повторяем поиск. Если снова пусто, значит заказов нет в принципе.
        async with async_session() as session:
            # Ищем снова, но уже без учёта просмотренных, так как мы их очистили
            fresh_query = query.where(orders.c.order_id.notin_([])) 
            result = await session.execute(fresh_query)
            order = result.fetchone()

        if order:
            await message.answer("Вы просмотрели все новые заказы. Показываю их заново.")
            await show_next_order(message_or_call, state) # Рекурсивный вызов
        else:
            await state.clear()
            await message.answer("На данный момент активных заказов нет. Загляните позже!", reply_markup=kb.get_main_menu_keyboard())

@dp.callback_query(F.data.startswith('apply_'))
async def apply_for_job(call: types.CallbackQuery, state: FSMContext):
    order_id = int(call.data.split('_')[1])
    worker = await get_user(call.from_user.id)
    
    async with async_session() as session:
        # Получаем информацию о заказе и его владельце
        result = await session.execute(select(orders).where(orders.c.order_id == order_id))
        order = result.fetchone()

    if not order or not worker:
        await call.answer("Произошла ошибка, заказ или профиль не найден.", show_alert=True)
        return

    # Отправляем уведомление заказчику
    try:
        profile_text = format_user_profile(worker)
        await bot.send_message(
            order.employer_id,
            f"✉️ <b>Новый отклик на ваш заказ «{order.title}»!</b>\n\n"
            f"Профиль исполнителя:\n{profile_text}"
        )
        await call.answer("✅ Ваш отклик успешно отправлен заказчику!", show_alert=True)
    except Exception as e:
        logger.error(f"Не удалось отправить отклик от {worker.user_id} на заказ {order_id}: {e}")
        await call.answer("Не удалось отправить отклик. Возможно, заказчик заблокировал бота.", show_alert=True)
    
    # Показываем следующий заказ
    await call.message.delete()
    await show_next_order(call, state)

@dp.callback_query(F.data == 'skip_order')
async def skip_job(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()
    await show_next_order(call, state)

@dp.callback_query(F.data == 'stop_search')
async def stop_search(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer("Поиск завершен.", reply_markup=kb.get_main_menu_keyboard())


# --- УПРАВЛЕНИЕ ЗАКАЗАМИ (Callbacks) ---

@dp.callback_query(F.data.startswith('close_order_'))
async def close_order(call: types.CallbackQuery):
    order_id = int(call.data.split('_')[2])
    async with async_session() as session:
        stmt = update(orders).where(and_(orders.c.order_id == order_id, orders.c.employer_id == call.from_user.id)).values(status='closed')
        await session.execute(stmt)
        await session.commit()
    await call.message.edit_text(f"Заказ #{order_id} был закрыт. Он больше не будет отображаться в поиске.")
    await call.answer()

@dp.callback_query(F.data.startswith('reopen_order_'))
async def reopen_order(call: types.CallbackQuery):
    order_id = int(call.data.split('_')[2])
    async with async_session() as session:
        stmt = update(orders).where(and_(orders.c.order_id == order_id, orders.c.employer_id == call.from_user.id)).values(status='open')
        await session.execute(stmt)
        await session.commit()
    await call.message.edit_text(f"Заказ #{order_id} снова открыт и доступен для поиска.")
    await call.answer()

@dp.callback_query(F.data.startswith('delete_order_'))
async def delete_order_prompt(call: types.CallbackQuery):
    order_id = int(call.data.split('_')[2])
    await call.message.edit_text(
        f"Вы уверены, что хотите <b>безвозвратно</b> удалить заказ #{order_id}?\n"
        "Все связанные с ним данные (отклики и т.д.) также будут удалены.",
        reply_markup=kb.get_confirm_delete_keyboard(order_id)
    )
    await call.answer()

@dp.callback_query(F.data.startswith('confirm_delete_'))
async def confirm_delete_order(call: types.CallbackQuery):
    order_id = int(call.data.split('_')[2])
    async with async_session() as session:
        # ВАЖНО: ondelete="CASCADE" в `database.py` должен позаботиться об удалении откликов.
        # Если нет, то сначала нужно удалить отклики:
        # await session.execute(delete(applications).where(applications.c.order_id == order_id))
        stmt = delete(orders).where(and_(orders.c.order_id == order_id, orders.c.employer_id == call.from_user.id))
        await session.execute(stmt)
        await session.commit()
    await call.message.edit_text(f"Заказ #{order_id} был полностью удален.")
    await call.answer("Заказ удален.")

@dp.callback_query(F.data == 'cancel_delete')
async def cancel_delete_order(call: types.CallbackQuery):
    await call.message.delete()
    await call.message.answer("Удаление отменено.")
    await call.answer()

# --- РЕДАКТИРОВАНИЕ ПРОФИЛЯ ---

@dp.callback_query(F.data == "edit_profile")
async def handle_edit_profile(call: types.CallbackQuery):
    """Показывает меню редактирования профиля."""
    await call.message.edit_text(
        "Что именно вы хотите изменить?",
        reply_markup=kb.get_edit_profile_keyboard()
    )
    await call.answer()

@dp.callback_query(F.data == "back_to_profile")
async def handle_back_to_profile(call: types.CallbackQuery, state: FSMContext):
    """Возвращает к отображению профиля."""
    await state.clear()
    await call.message.delete()
    await handle_my_profile(call.message) # Вызываем основной обработчик профиля
    await call.answer()

@dp.callback_query(F.data == "toggle_visibility")
async def handle_toggle_visibility(call: types.CallbackQuery):
    """Переключает видимость профиля."""
    user = await get_user(call.from_user.id)
    new_status = not user.is_active

    async with async_session() as session:
        await session.execute(
            update(users).where(users.c.user_id == call.from_user.id).values(is_active=new_status)
        )
        await session.commit()
    
    await call.answer(f"Ваш профиль теперь {'виден' if new_status else 'скрыт'} в поиске.")
    
    # Обновляем сообщение с профилем
    await call.message.delete()
    await handle_my_profile(call.message)

@dp.callback_query(F.data.startswith("edit_"))
async def select_field_to_edit(call: types.CallbackQuery, state: FSMContext):
    """Запускает FSM для изменения выбранного поля."""
    field = call.data.split("_")[1]
    
    prompts = {
        "name": "Введите ваше новое имя:",
        "sphere": "Укажите новую сферу деятельности:",
        "bio": "Введите новое описание 'О себе':",
        "portfolio": "Отправьте новую ссылку на портфолио (или '-' для удаления):",
        "role": "Выберите вашу новую роль:"
    }

    await state.set_state(ProfileEditing.new_value)
    await state.update_data(field_to_edit=field)
    
    if field == "role":
        await call.message.answer(prompts[field], reply_markup=kb.get_role_selection_keyboard())
    else:
        await call.message.answer(prompts[field], reply_markup=types.ReplyKeyboardRemove())
    
    await call.message.delete()
    await call.answer()

@dp.message(ProfileEditing.new_value)
async def process_new_profile_value(message: types.Message, state: FSMContext):
    """Обрабатывает новое значение от пользователя и обновляет БД."""
    data = await state.get_data()
    field = data["field_to_edit"]
    
    value = message.text
    
    # Обрабатываем выбор роли
    if field == "role":
        role_map = {
            "Я ищу работу (Исполнитель)": "worker",
            "Я ищу исполнителя (Заказчик)": "employer",
            "И то, и другое": "both"
        }
        role = role_map.get(message.text)
        if not role:
            await message.answer("Пожалуйста, выберите роль с помощью кнопок.", reply_markup=kb.get_role_selection_keyboard())
            return
        value = role

    # Для портфолио обрабатываем прочерк
    if field == "portfolio" and value == "-":
        value = None
        
    async with async_session() as session:
        await session.execute(
            update(users).where(users.c.user_id == message.from_user.id).values({field: value})
        )
        await session.commit()

    await message.answer("✅ Данные успешно обновлены!", reply_markup=kb.get_main_menu_keyboard())
    
    await state.clear()
    await handle_my_profile(message) # Показываем обновленный профиль

# --- ЗАПУСК БОТА ---
async def main():
    logger.info("Запуск бота...")
    await create_tables()  # Создаем таблицы при запуске
    # Очищаем таблицу просмотренных заказов при каждом запуске бота
    async with async_session() as session:
        await session.execute(delete(viewed_orders))
        await session.commit()
    
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())