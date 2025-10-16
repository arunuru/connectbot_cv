# Файл: config.py

import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла в окружение
load_dotenv()

class Config:
    # --- Основные настройки бота ---
    # Токен твоего бота, полученный у @BotFather
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # --- Настройки базы данных ---
    # URL для подключения к PostgreSQL. Формат: "postgresql+asyncpg://user:password@host:port/dbname"
    DB_URL = os.getenv("DB_URL")

    # --- Настройки группы и веток (топиков) ---
    # ID основной группы для нетворкинга
    NETWORKING_GROUP_ID = int(os.getenv("NETWORKING_GROUP_ID", 0))
    NETWORKING_TOPIC_ID = int(os.getenv("NETWORKING_TOPIC_ID", 0))
    ORDERS_TOPIC_ID = int(os.getenv("ORDERS_TOPIC_ID", 0))

    # --- Настройки логики ---
    # Через сколько часов заказ считается "протухшим"
    ORDER_LIFETIME_HOURS = 48

    # --- Настройки Google Sheets ---
    # Имя JSON-файла с ключами для доступа к Google API (должен лежать рядом с ботом)
    GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "credentials.json")
    
    # Название твоей Google таблицы
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))