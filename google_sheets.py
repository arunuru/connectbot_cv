import gspread_asyncio
from google.oauth2.service_account import Credentials
from config import Config
import logging


logger = logging.getLogger(__name__)

def get_creds():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_file(Config.GOOGLE_CREDS_JSON, scopes=scopes)

agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

async def get_sheets():
    """Асинхронно подключается к Google и возвращает объекты листов."""
    try:
        agc = await agcm.authorize()
        spreadsheet = await agc.open(Config.GOOGLE_SHEET_NAME)
        users_sheet = await spreadsheet.worksheet("Пользователи")
        orders_sheet = await spreadsheet.worksheet("Заказы")
        return users_sheet, orders_sheet
    except Exception as e:
        logger.error(f"Не удалось подключиться к Google Sheets или найти листы 'Пользователи'/'Заказы': {e}")
        return None, None

async def add_user_to_sheet(user_data: dict):
    """Добавляет нового пользователя в Google Таблицу."""
    users_sheet, _ = await get_sheets()
    if not users_sheet:
        return

    try:
        header = await users_sheet.row_values(1)
        if not header:
            headers = ["ID Пользователя", "Username", "Полное имя", "Роль", "Сфера", "О себе", "Портфолио", "Дата регистрации"]
            await users_sheet.append_row(headers)

        row = [
            user_data.get('user_id'),
            user_data.get('username'),
            user_data.get('full_name'),
            user_data.get('role'),
            user_data.get('sphere'),
            user_data.get('bio'),
            user_data.get('portfolio', '-'),
            user_data.get('created_at').strftime('%Y-%m-%d %H:%M:%S')
        ]
        await users_sheet.append_row(row)
        logger.info(f"Пользователь {user_data.get('user_id')} успешно добавлен в Google Sheets.")
    except Exception as e:
        logger.error(f"Не удалось добавить пользователя {user_data.get('user_id')} в таблицу: {e}")

async def add_order_to_sheet(order_data: dict, employer_username: str):
    """Добавляет новый заказ в Google Таблицу."""
    _, orders_sheet = await get_sheets()
    if not orders_sheet:
        return

    try:
        header = await orders_sheet.row_values(1)
        if not header:
            headers = ["ID Заказа", "ID Заказчика", "Username Заказчика", "Название", "Описание", "Дата создания", "Статус"]
            await orders_sheet.append_row(headers)

        row = [
            order_data.get('order_id'),
            order_data.get('employer_id'),
            employer_username,
            order_data.get('title'),
            order_data.get('description'),
            order_data.get('created_at').strftime('%Y-%m-%d %H:%M:%S'),
            order_data.get('status', 'open')
        ]
        await orders_sheet.append_row(row)
        logger.info(f"Заказ {order_data.get('order_id')} успешно добавлен в Google Sheets.")
    except Exception as e:
        logger.error(f"Не удалось добавить заказ {order_data.get('order_id')} в таблицу: {e}")
