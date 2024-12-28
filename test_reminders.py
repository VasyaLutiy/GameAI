import asyncio
import pytest
from datetime import datetime, timedelta
import pytz
from database import init_db, get_db, get_or_create_user, create_reminder

def setup_module():
    """Инициализация базы данных перед тестами"""
    init_db()

def test_db_connection():
    """Проверка подключения к базе данных"""
    with get_db() as db:
        assert db is not None

def test_user_creation():
    """Проверка создания пользователя"""
    with get_db() as db:
        user = get_or_create_user(
            db, 
            telegram_id=123456,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        assert user is not None
        assert user.telegram_id == 123456
        assert user.username == "test_user"

def test_reminder_creation():
    """Проверка создания напоминания"""
    with get_db() as db:
        # Создаем тестового пользователя
        user = get_or_create_user(db, telegram_id=123456)
        
        # Создаем напоминание через 5 минут
        reminder_time = datetime.now(pytz.UTC) + timedelta(minutes=5)
        reminder = create_reminder(
            db,
            user_id=user.id,
            chat_id=123456,
            title="Тестовое напоминание",
            reminder_time=reminder_time
        )
        
        assert reminder is not None
        assert reminder.title == "Тестовое напоминание"
        assert reminder.user_id == user.id
        assert reminder.telegram_chat_id == 123456
        assert not reminder.reminder_sent
        
        # Проверяем форматирование времени
        formatted_time = reminder.formatted_datetime
        assert isinstance(formatted_time, str)
        print(f"Форматированное время: {formatted_time}")

def test_reminder_parsing():
    """Тест парсинга времени из сообщения"""
    import re
    
    test_messages = [
        "Напомни в 15:30 про встречу",
        "напоминание на 9:00 принять лекарство",
        "Напомни в 23:59 лечь спать",
        "напомни в 8:05 позвонить маме"
    ]
    
    for message in test_messages:
        # Ищем время в формате ЧЧ:ММ
        time_match = re.search(r'(\d{1,2})[:-](\d{2})', message)
        assert time_match is not None, f"Не удалось найти время в сообщении: {message}"
        
        hours, minutes = map(int, time_match.groups())
        assert 0 <= hours <= 23, f"Некорректные часы в сообщении: {message}"
        assert 0 <= minutes <= 59, f"Некорректные минуты в сообщении: {message}"
        
        # Извлекаем текст напоминания
        title = message.lower()
        patterns = [
            "напомни в", "напоминание на", "напомни", "напоминание",
            f"{hours}:{minutes:02d}", f"{hours}:{minutes}",
            "в ", "на "
        ]
        for pattern in patterns:
            title = title.replace(pattern.lower(), "").strip()
        
        assert len(title) > 0, f"Не удалось извлечь текст напоминания из сообщения: {message}"
        print(f"Сообщение: {message}")
        print(f"Время: {hours:02d}:{minutes:02d}")
        print(f"Текст: {title}")
        print("---")

if __name__ == "__main__":
    print("Запуск тестов напоминаний...")
    setup_module()
    test_db_connection()
    test_user_creation()
    test_reminder_creation()
    test_reminder_parsing()
    print("Все тесты успешно пройдены!")