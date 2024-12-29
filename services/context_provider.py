import logging
from typing import Optional
from database import get_db
from models.user import User
from services.summarization import SummaryManager

logger = logging.getLogger(__name__)

class SummaryContextProvider:
    def __init__(self):
        self.summary_manager = SummaryManager()
        self.recent_messages_limit = 20

    async def get_context(self, message: str, user_id: int) -> str:
        """
        Формирует контекст для ответа, используя:
        1. Общее саммари всей истории
        2. Последние N сообщений
        """
        try:
            with get_db() as db:
                user = db.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    return ""

                # Проверяем необходимость создания новых саммари
                await self.summary_manager.check_and_create_summaries(user_id)

                # Получаем цепочку саммари
                summary_context = user.get_summary_chain()

                # Получаем последние сообщения
                recent_messages = self._format_recent_messages(
                    user.get_recent_dialogs(self.recent_messages_limit)
                )

                # Формируем полный контекст
                context_parts = [
                    "История диалогов:",
                    summary_context,
                    "\nПоследние сообщения:",
                    recent_messages
                ]

                return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return ""

    def _format_recent_messages(self, messages: list) -> str:
        """Форматирует последние сообщения для контекста"""
        formatted = []
        for msg in messages:
            formatted.append(f"User: {msg.message}")
            formatted.append(f"Assistant: {msg.response}")
        return "\n".join(formatted)