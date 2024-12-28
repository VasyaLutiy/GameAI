"""Тесты для функциональности истории диалогов"""
import pytest
from datetime import datetime, timedelta
import pytz
from database import get_db, get_or_create_user, save_dialog
from models.chat_history import ChatHistory
from models.user import User
from dialog_manager import DialogHistoryManager

def cleanup_test_data(test_user_id: int):
    """Очистка тестовых данных"""
    with get_db() as db:
        # Находим тестового пользователя
        user = db.query(User).filter_by(telegram_id=test_user_id).first()
        if user:
            # Удаляем все его диалоги
            db.query(ChatHistory).filter_by(user_id=user.id).delete()
            # Удаляем самого пользователя
            db.delete(user)
            db.commit()

@pytest.mark.asyncio
async def test_save_and_retrieve_dialog():
    """Тест сохранения и получения диалогов"""
    test_user_id = 999999  # Тестовый Telegram ID
    
    # Очищаем тестовые данные перед тестом
    cleanup_test_data(test_user_id)
    
    with get_db() as db:
        # Создаем тестового пользователя
        user = get_or_create_user(db, telegram_id=test_user_id, username="test_user")
        
        # Сохраняем тестовый диалог
        test_dialogs = [
            ("Привет!", "Здравствуйте!", "default"),
            ("Как дела?", "Все хорошо!", "default"),
            ("Переключись в кибер режим", "Инициализация...", "cyber"),
        ]
        
        for message, response, mode in test_dialogs:
            save_dialog(db, user.id, message, response, mode)
            
        # Получаем диалоги через DialogHistoryManager
        dialog_manager = DialogHistoryManager()
        
        # Тест получения последних диалогов
        recent_dialogs = dialog_manager.get_recent_dialogs(test_user_id, limit=5)
        assert len(recent_dialogs) == 3, "Должно быть 3 диалога"
        assert isinstance(recent_dialogs[0], dict), "Диалоги должны быть в формате словаря"
        assert all(isinstance(d, dict) for d in recent_dialogs), "Все диалоги должны быть словарями"
        
        # Проверяем структуру словаря
        first_dialog = recent_dialogs[0]
        assert all(key in first_dialog for key in ['message', 'response', 'character_mode', 'timestamp']), \
            "Диалог должен содержать все необходимые поля"
        
        # Тест получения диалогов по характеру
        default_dialogs = dialog_manager.get_character_dialogs(
            test_user_id, "default", limit=5
        )
        assert len(default_dialogs) == 2, "Должно быть 2 диалога в режиме default"
        assert all(d['character_mode'] == 'default' for d in default_dialogs), \
            "Все диалоги должны быть в режиме default"
        
        cyber_dialogs = dialog_manager.get_character_dialogs(
            test_user_id, "cyber", limit=5
        )
        assert len(cyber_dialogs) == 1, "Должен быть 1 диалог в режиме cyber"
        assert cyber_dialogs[0]['character_mode'] == 'cyber', \
            "Диалог должен быть в режиме cyber"
        
        # Проверяем форматирование для контекста
        context = dialog_manager.format_dialogs_for_context(recent_dialogs)
        assert "Привет!" in context, "Контекст должен содержать сообщение"
        assert "Здравствуйте!" in context, "Контекст должен содержать ответ"
        
        # Проверяем содержимое диалогов
        messages = [d['message'] for d in recent_dialogs]
        responses = [d['response'] for d in recent_dialogs]
        assert "Привет!" in messages, "Должно быть сообщение 'Привет!'"
        assert "Здравствуйте!" in responses, "Должен быть ответ 'Здравствуйте!'"

@pytest.mark.asyncio
async def test_dialog_provider():
    """Тест провайдера контекста с историей диалогов"""
    from test_vasilia import VasilisaLLM
    from database import get_db, save_dialog
    
    test_user_id = 999999
    test_message = "Тестовое сообщение"
    
    # Очищаем тестовые данные перед тестом
    cleanup_test_data(test_user_id)
    
    # Создаем тестовые данные
    with get_db() as db:
        user = get_or_create_user(db, telegram_id=test_user_id, username="test_user")
        save_dialog(db, user.id, "Привет!", "Здравствуйте!", "default")
        save_dialog(db, user.id, "Как дела?", "Отлично!", "default")
    
    # Тестируем провайдер истории
    vasilia = VasilisaLLM(context_provider="history")
    history_context = vasilia.history_content(
        message=test_message,
        user_id=test_user_id
    )
    
    # Проверяем контекст истории
    assert history_context is not None
    assert "Привет!" in history_context
    assert "Здравствуйте!" in history_context
    
    # Тестируем комбинированный провайдер
    vasilia = VasilisaLLM(context_provider="combined")
    combined_context = vasilia.combined_content(
        message=test_message,
        user_id=test_user_id
    )
    
    # Проверяем наличие обоих типов контекста
    assert "Базовые примеры диалогов:" in combined_context
    assert "Привет!" in combined_context
    assert "Здравствуйте!" in combined_context
    
    # Проверяем форматирование
    assert "User:" in combined_context
    assert "Assistant" in combined_context

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])