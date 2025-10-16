# Файл: keyboards.py

from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)

# --- Reply-клавиатуры (основные кнопки) ---

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="🔍 Найти работу")],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="➕ Создать заказ")]
        ],
        resize_keyboard=True
    )

def get_role_selection_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Я ищу работу (Исполнитель)")],
            [KeyboardButton(text="Я ищу исполнителя (Заказчик)")],
            [KeyboardButton(text="И то, и другое")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_confirm_publication_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да, опубликовать"), KeyboardButton(text="Нет, пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# --- Inline-клавиатуры (кнопки под сообщениями) ---

def get_profile_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")]
        ]
    )

def get_edit_profile_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Имя", callback_data="edit_name"), InlineKeyboardButton(text="Сфера", callback_data="edit_sphere")],
            [InlineKeyboardButton(text="О себе", callback_data="edit_bio"), InlineKeyboardButton(text="Портфолио", callback_data="edit_portfolio")],
            [InlineKeyboardButton(text="Роль", callback_data="edit_role")],
            [InlineKeyboardButton(text="👀 Статус видимости", callback_data="toggle_visibility")],
            [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")]
        ]
    )
    
def get_job_search_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Откликнуться", callback_data=f"apply_{order_id}"),
                InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_order")
            ],
            [InlineKeyboardButton(text="🚪 Закончить поиск", callback_data="stop_search")]
        ]
    )

def get_order_management_keyboard(order_id: int, is_closed: bool):
    buttons = []
    if is_closed:
        buttons.append(InlineKeyboardButton(text="🚀 Открыть заказ снова", callback_data=f"reopen_order_{order_id}"))
    else:
        buttons.append(InlineKeyboardButton(text="🔒 Закрыть заказ", callback_data=f"close_order_{order_id}"))
    
    buttons.append(InlineKeyboardButton(text="🗑️ Удалить заказ", callback_data=f"delete_order_{order_id}"))

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def get_confirm_delete_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{order_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
            ]
        ]
    )