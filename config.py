import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    DB_URL = os.getenv("DB_URL")

    NETWORKING_GROUP_ID = int(os.getenv("NETWORKING_GROUP_ID", 0))
    NETWORKING_TOPIC_ID = int(os.getenv("NETWORKING_TOPIC_ID", 0))
    ORDERS_TOPIC_ID = int(os.getenv("ORDERS_TOPIC_ID", 0))
    ORDER_LIFETIME_HOURS = 48
    # --- Настройки Google Sheets ---
    # Имя JSON-файла с ключами для доступа к Google API (должен лежать рядом с ботом)
    GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "credentials.json")    
    # Название твоей Google таблицы
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
