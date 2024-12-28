from datetime import datetime
import logging
from typing import List, Optional

from database import get_db, get_or_create_user
from models.chat_history import ChatHistory

logger = logging.getLogger(__name__)

class DialogHistoryManager:
    """Менеджер для работы с историей диалогов"""
    
    def save_dialog(self, telegram_id: int, message: str, response: str, 
                   character_mode: str) -> Optional[ChatHistory]:
        """Сохранить диалог в историю"""
        try:
            with get_db() as db:
                # Получаем или создаем пользователя
                user = get_or_create_user(db, telegram_id)
                
                # Создаем запись диалога
                dialog = ChatHistory.create_dialog_entry(
                    user_id=user.id,
                    message=message,
                    response=response,
                    character_mode=character_mode
                )
                
                db.add(dialog)
                db.commit()
                logger.info(f"Диалог сохранен для пользователя {telegram_id}")
                return dialog
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении диалога: {e}")
            return None
    
    def get_recent_dialogs(self, telegram_id: int, limit: int = 5) -> List[dict]:
        """Получить последние диалоги пользователя"""
        try:
            with get_db() as db:
                user = get_or_create_user(db, telegram_id)
                # Получаем диалоги напрямую через запрос
                dialogs = (db.query(ChatHistory)
                          .filter(ChatHistory.user_id == user.id)
                          .order_by(ChatHistory.timestamp.desc())
                          .limit(limit)
                          .all())
                
                # Преобразуем в словари до закрытия сессии
                return [
                    {
                        'message': d.message,
                        'response': d.response,
                        'character_mode': d.character_mode,
                        'timestamp': d.timestamp
                    }
                    for d in dialogs
                ]
        except Exception as e:
            logger.error(f"Ошибка при получении диалогов: {e}")
            return []
    
    def get_character_dialogs(self, telegram_id: int, 
                            character_mode: str, limit: int = 5) -> List[dict]:
        """Получить диалоги пользователя с определенным характером бота"""
        try:
            with get_db() as db:
                user = get_or_create_user(db, telegram_id)
                # Получаем диалоги напрямую через запрос
                dialogs = (db.query(ChatHistory)
                          .filter(ChatHistory.user_id == user.id)
                          .filter(ChatHistory.character_mode == character_mode)
                          .order_by(ChatHistory.timestamp.desc())
                          .limit(limit)
                          .all())
                
                # Преобразуем в словари до закрытия сессии
                return [
                    {
                        'message': d.message,
                        'response': d.response,
                        'character_mode': d.character_mode,
                        'timestamp': d.timestamp
                    }
                    for d in dialogs
                ]
        except Exception as e:
            logger.error(f"Ошибка при получении диалогов для характера {character_mode}: {e}")
            return []
    
    def format_dialogs_for_context(self, dialogs: List[dict], 
                                 max_length: int = 1000) -> str:
        """Форматировать диалоги для использования в контексте"""
        if not dialogs:
            return ""
        
        context = []
        total_length = 0
        
        for dialog in dialogs:
            dialog_text = f"User: {dialog['message']}\nAssistant ({dialog['character_mode']}): {dialog['response']}"
            if total_length + len(dialog_text) > max_length:
                break
            context.append(dialog_text)
            total_length += len(dialog_text)
        
        return "\n\n".join(context)
    
    def clear_old_dialogs(self, days_to_keep: int = 30) -> int:
        """Удалить старые диалоги"""
        try:
            with get_db() as db:
                from datetime import timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                
                # Удаляем старые диалоги
                result = db.query(ChatHistory).filter(
                    ChatHistory.timestamp < cutoff_date
                ).delete()
                
                db.commit()
                logger.info(f"Удалено {result} старых диалогов")
                return result
                
        except Exception as e:
            logger.error(f"Ошибка при очистке старых диалогов: {e}")
            return 0