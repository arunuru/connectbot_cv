import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy import (Table, Column, Integer, BigInteger, String, Text,
                        Boolean, TIMESTAMP, ForeignKey, MetaData, select, update, delete, and_, insert)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import Config

engine = create_async_engine(Config.DB_URL)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
metadata = MetaData()

users = Table(
    'users', metadata,
    Column('user_id', BigInteger, primary_key=True, unique=True),
    Column('username', String(255)),
    Column('full_name', String(255), nullable=False),
    Column('bio', Text),
    Column('sphere', String(255)),
    Column('portfolio', String(255)),
    Column('role', String(50), nullable=False),  
    Column('is_active', Boolean, default=True), 
    Column('created_at', TIMESTAMP, default=datetime.now)
)

orders = Table(
    'orders', metadata,
    Column('order_id', Integer, primary_key=True, autoincrement=True),
    Column('employer_id', BigInteger, ForeignKey('users.user_id', ondelete="CASCADE")),
    Column('title', String(255), nullable=False),
    Column('description', Text, nullable=False),
    Column('photo_id', String(255)),
    Column('status', String(50), default='open'),  
    Column('created_at', TIMESTAMP, default=datetime.now)
)

applications = Table(
    'applications', metadata,
    Column('application_id', Integer, primary_key=True, autoincrement=True),
    Column('order_id', Integer, ForeignKey('orders.order_id', ondelete="CASCADE")),
    Column('worker_id', BigInteger, ForeignKey('users.user_id', ondelete="CASCADE")),
    Column('created_at', TIMESTAMP, default=datetime.now),
    Column('status', String(50), default='pending') 
)

viewed_orders = Table(
    'viewed_orders', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('viewer_id', BigInteger, ForeignKey('users.user_id', ondelete="CASCADE")),
    Column('order_id', Integer, ForeignKey('orders.order_id', ondelete="CASCADE")),
    Column('viewed_at', TIMESTAMP, default=datetime.now)
)

async def create_tables():
    """Создает все таблицы в базе данных, если их еще нет."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    print("Таблицы успешно созданы или уже существуют.")


if __name__ == '__main__':
    asyncio.run(create_tables())
