import logging
from typing import List, Dict, Optional
from datetime import datetime

from database import get_db
from models.dialog_summary import DialogSummary
from models.chat_history import ChatHistory

logger = logging.getLogger(__name__)

class DialogSummarizer:
    def __init__(self):
        self.messages_threshold = 20
        self.summaries_threshold = 5
        
    async def create_summary(self, messages: List[Dict], level: int) -> str:
        """Создает саммари через Claude"""
        prompt = self._build_summary_prompt(messages, level)
        try:
            # TODO: Реализовать вызов Claude через litellm_proxy
            from test_vasilia import VasilisaLLM
            llm = VasilisaLLM()
            response = await llm.get_response(prompt)
            return response
        except Exception as e:
            logger.error(f"Error creating summary: {e}")
            return None

    def _build_summary_prompt(self, messages: List[Dict], level: int) -> str:
        """Создает промпт для суммаризации"""
        if level == 1:
            return f"""
            Создай информативное саммари диалога из {len(messages)} сообщений.
            Сохрани:
            - Основные темы и подтемы
            - Ключевые факты и договоренности
            - Эмоциональный контекст
            - Незавершенные вопросы
            
            Диалог:
            {self._format_messages(messages)}
            """
        else:
            return f"""
            Объедини {len(messages)} саммари в одно общее.
            Сохрани хронологию и взаимосвязи тем.
            
            Предыдущие саммари:
            {self._format_summaries(messages)}
            """

    def _format_messages(self, messages: List[Dict]) -> str:
        """Форматирует сообщения для промпта"""
        formatted = []
        for msg in messages:
            formatted.append(f"User: {msg['message']}")
            formatted.append(f"Assistant: {msg['response']}")
        return "\n".join(formatted)

    def _format_summaries(self, summaries: List[Dict]) -> str:
        """Форматирует саммари для промпта"""
        return "\n\n".join([s['summary_text'] for s in summaries])

class SummaryManager:
    def __init__(self):
        self.summarizer = DialogSummarizer()
        
    async def check_and_create_summaries(self, user_id: int):
        """Проверяет необходимость создания новых саммари"""
        try:
            # Проверяем необходимость Level 1 саммари
            messages = await self._get_unsummarized_messages(user_id)
            if len(messages) >= self.summarizer.messages_threshold:
                summary = await self.summarizer.create_summary(messages, level=1)
                if summary:
                    await self._save_summary(summary, messages, level=1)
                
            # Проверяем необходимость Level 2 саммари
            l1_summaries = await self._get_level1_summaries(user_id)
            if len(l1_summaries) >= self.summarizer.summaries_threshold:
                l2_summary = await self.summarizer.create_summary(l1_summaries, level=2)
                if l2_summary:
                    await self._save_summary(l2_summary, l1_summaries, level=2)
        except Exception as e:
            logger.error(f"Error in check_and_create_summaries: {e}")

    async def _get_unsummarized_messages(self, user_id: int) -> List[Dict]:
        """Получает сообщения, которые еще не были суммаризированы"""
        with get_db() as db:
            # Получаем последний summary для определения точки отсчета
            last_summary = db.query(DialogSummary).filter(
                DialogSummary.user_id == user_id,
                DialogSummary.level == 1
            ).order_by(DialogSummary.end_message_id.desc()).first()
            
            # Получаем новые сообщения после последнего саммари
            start_id = last_summary.end_message_id + 1 if last_summary else 0
            messages = db.query(ChatHistory).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.id > start_id
            ).order_by(ChatHistory.id.asc()).all()
            
            return [
                {
                    'message': m.message,
                    'response': m.response,
                    'timestamp': m.timestamp
                }
                for m in messages
            ]

    async def _get_level1_summaries(self, user_id: int) -> List[Dict]:
        """Получает саммари первого уровня"""
        with get_db() as db:
            summaries = db.query(DialogSummary).filter(
                DialogSummary.user_id == user_id,
                DialogSummary.level == 1
            ).order_by(DialogSummary.id.desc()).limit(self.summarizer.summaries_threshold).all()
            
            return [
                {
                    'summary_text': s.summary_text,
                    'created_at': s.created_at
                }
                for s in summaries
            ]

    async def _save_summary(self, summary_text: str, messages: List[Dict], level: int):
        """Сохраняет созданное саммари в базу"""
        with get_db() as db:
            summary = DialogSummary(
                user_id=messages[0]['user_id'],
                summary_text=summary_text,
                start_message_id=messages[0]['id'],
                end_message_id=messages[-1]['id'],
                level=level
            )
            db.add(summary)
            db.commit()
            logger.info(f"Saved level {level} summary for user {messages[0]['user_id']}")