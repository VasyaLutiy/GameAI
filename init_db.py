"""Скрипт для инициализации базы данных"""
from database import init_db
import logging

# Import all models to ensure they are registered with SQLAlchemy
from models.user import User
from models.event import Event
from models.chat_history import ChatHistory
from models.note import Note

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")