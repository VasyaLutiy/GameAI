from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import os

from models.base import Base  # Импортируем Base из отдельного файла
from models.user import User
from models.event import Event
from models.chat_history import ChatHistory
from models.note import Note  # Добавляем импорт Note

# Создаем подключение к базе данных SQLite
DATABASE_URL = "sqlite:///bot_database.db"
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

@contextmanager
def get_db():
    """Контекстный менеджер для работы с сессией базы данных"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(engine)

def get_or_create_user(session, telegram_id: int, **kwargs):
    """Получает существующего пользователя или создает нового"""
    import logging
    logger = logging.getLogger(__name__)
    from models.user import User
    
    try:
        logger.info(f"Looking for user with telegram_id={telegram_id}")
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if not user:
            logger.info(f"Creating new user with telegram_id={telegram_id}")
            user = User(telegram_id=telegram_id, **kwargs)
            session.add(user)
            session.commit()
            logger.info(f"New user created with id={user.id}")
        else:
            logger.info(f"Found existing user with id={user.id}")
        return user
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {str(e)}")
        raise e

def create_reminder(session, user_id: int, chat_id: int, title: str, reminder_time, description: str = None):
    """Создает новое напоминание"""
    try:
        # Проверяем, нет ли уже такого напоминания
        existing_reminder = session.query(Event).filter(
            Event.user_id == user_id,
            Event.title == title,
            Event.datetime == reminder_time,
            Event.reminder_sent == False
        ).first()
        
        if existing_reminder:
            return existing_reminder
            
        # Создаем новое напоминание
        reminder = Event.create_reminder(
            user_id=user_id,
            chat_id=chat_id,
            title=title,
            reminder_time=reminder_time,
            description=description
        )
        session.add(reminder)
        session.flush()  # Убеждаемся, что объект создан в базе
        session.refresh(reminder)  # Обновляем объект из базы
        session.commit()
        return reminder
    except Exception as e:
        session.rollback()
        raise e

def get_active_reminders(session, user_id: int):
    """Получает список активных напоминаний пользователя"""
    from datetime import datetime
    import pytz
    
    # Получаем текущее время в UTC
    now = datetime.now(pytz.UTC)
    
    # Получаем все неотправленные напоминания для пользователя
    reminders = session.query(Event).filter(
        Event.user_id == user_id,
        Event.reminder_sent == False
    ).order_by(Event.datetime.asc()).all()
    
    # Фильтруем напоминания, учитывая часовой пояс
    active_reminders = []
    for reminder in reminders:
        # Если дата в базе без часового пояса, добавляем UTC
        if reminder.datetime.tzinfo is None:
            reminder_time = pytz.UTC.localize(reminder.datetime)
        else:
            reminder_time = reminder.datetime
            
        if reminder_time >= now:
            active_reminders.append(reminder)
            
    return active_reminders

def mark_reminder_sent(session, reminder_id: int):
    """Отмечает напоминание как отправленное"""
    reminder = session.query(Event).get(reminder_id)
    if reminder:
        reminder.reminder_sent = True
        session.commit()

def save_dialog(session, user_id: int, message: str, response: str, character_mode: str):
    """Сохраняет диалог в историю"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Creating dialog entry for user_id={user_id}")
        dialog = ChatHistory.create_dialog_entry(
            user_id=user_id,
            message=message,
            response=response,
            character_mode=character_mode
        )
        logger.info("Dialog entry created, adding to session")
        session.add(dialog)
        logger.info("Committing dialog to database")
        session.commit()
        logger.info(f"Dialog saved successfully with id={dialog.id}")
        return dialog
    except Exception as e:
        logger.error(f"Error in save_dialog: {str(e)}")
        session.rollback()
        raise e

def get_user_dialog_history(session, user_id: int, limit: int = 5):
    """Получает последние диалоги пользователя"""
    return session.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()

def get_character_dialog_history(session, user_id: int, character_mode: str, limit: int = 5):
    """Получает диалоги пользователя с определенным характером бота"""
    return session.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.character_mode == character_mode
    ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()