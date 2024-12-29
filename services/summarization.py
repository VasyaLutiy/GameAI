import logging
from typing import List, Dict, Optional
from datetime import datetime

from database import get_db
from models.dialog_summary import DialogSummary
from models.chat_history import ChatHistory
from models.user import User
from llm_integration import llm_manager

logger = logging.getLogger(__name__)

class DialogSummarizer:
    def __init__(self):
        self.messages_threshold = 5  # Уменьшаем порог для тестирования
        self.summaries_threshold = 3  # Уменьшаем и этот порог тоже
        
    async def create_summary(self, messages: List[Dict], level: int) -> str:
        """Создает саммари через Claude"""
        try:
            prompt = self._build_summary_prompt(messages, level)
            logger.info(f"Creating {level=} summary for {len(messages)} messages")
            logger.info(f"Summary prompt:\n{prompt}")
            
            # Создаем специальный промпт для саммари
            system_prompt = """Ты - профессиональный аналитик диалогов. Твоя задача - создать информативное саммари диалога.

Внимательно прочитай диалог и создай структурированное саммари, строго следуя формату:

Темы:
- Перечисли все темы, которые обсуждались в диалоге
- Каждая тема должна быть конкретной, например: "Знакомство", "Обсуждение возраста", "Работа с AI"

О пользователе:
- Перечисли все факты о пользователе из диалога
- Включи: имя, возраст, профессию, интересы и другие детали
- Каждый факт должен быть из диалога, не додумывай

Эмоции:
- Опиши эмоциональный тон диалога
- Укажи настроение и отношение собеседников
- Отметь изменения в эмоциональном фоне

Незавершенное:
- Перечисли вопросы, оставшиеся без ответа
- Укажи темы, требующие продолжения
- Отметь невыполненные обещания или планы

ВАЖНО:
1. Каждый раздел ДОЛЖЕН содержать минимум один пункт
2. Используй ТОЛЬКО информацию из диалога
3. Пиши кратко и по существу
4. Не добавляй свои предположения
5. Не используй технические маркеры (User:, Assistant:)
6. Строго следуй структуре разделов"""

            # Получаем саммари
            summary = await llm_manager.get_response(prompt, system_prompt=system_prompt)
            logger.info(f"Raw LLM response:\n{summary}")
            
            # Убираем возможные "User:" и "Assistant:" из саммари
            summary = summary.replace("User:", "").replace("Assistant:", "").strip()
            logger.info(f"Cleaned summary:\n{summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error creating summary: {e}", exc_info=True)
            return None

    def _build_summary_prompt(self, messages: List[Dict], level: int) -> str:
        """Создает промпт для суммаризации"""
        if level == 1:
            return f"""Проанализируй следующий диалог и создай его подробное саммари.

=== ДИАЛОГ (всего сообщений: {len(messages)}) ===
{self._format_messages(messages)}

Создай структурированное саммари, включив следующие разделы:

1. Темы диалога:
- Перечисли все обсуждаемые темы
- Укажи основные вопросы и проблемы
- Отметь ключевые моменты обсуждения

2. Информация о пользователе:
- Собери все упомянутые факты
- Укажи: имя, возраст, профессию, интересы
- Добавь другие важные детали из диалога

3. Эмоциональный контекст:
- Опиши общий тон беседы
- Отметь изменения настроения
- Укажи особенности взаимодействия

4. Незавершенные темы:
- Выдели открытые вопросы
- Укажи темы, требующие развития
- Отметь невыполненные обещания

Помни: каждый раздел должен содержать конкретную информацию из диалога."""
        else:
            return f"""Объедини несколько саммари в одно общее, сохраняя хронологию и контекст.

=== ПРЕДЫДУЩИЕ САММАРИ (всего: {len(messages)}) ===
{self._format_summaries(messages)}

Создай обобщенное саммари, включив следующие разделы:

1. Развитие тем:
- Объедини все обсуждавшиеся темы
- Покажи их развитие во времени
- Выдели главные и второстепенные темы

2. Портрет пользователя:
- Собери все факты о пользователе
- Построй целостный образ собеседника
- Отметь изменения в самопрезентации

3. Динамика эмоций:
- Опиши изменения в настроении диалога
- Отметь ключевые эмоциональные моменты
- Укажи общий эмоциональный фон

4. Открытые вопросы:
- Собери все незавершенные темы
- Выдели наиболее важные вопросы
- Отметь потенциальные направления развития

Помни: 
- Используй только информацию из саммари
- Сохраняй хронологию событий
- Объединяй повторяющиеся элементы
- Выделяй ключевые тенденции"""

    def _format_messages(self, messages: List[Dict]) -> str:
        """Форматирует сообщения для промпта"""
        formatted = []
        for i, msg in enumerate(messages, 1):
            # Форматируем время
            timestamp = msg['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if msg['timestamp'] else "??:??"
            
            # Добавляем сообщение с номером, временем и режимом
            formatted.append(f"=== Message #{i} ({timestamp}) ===")
            formatted.append(f"User: {msg['message']}")
            formatted.append(f"Assistant ({msg['character_mode']}): {msg['response']}")
            formatted.append("")  # Пустая строка для разделения
            
            # Добавляем разделитель для лучшей читаемости
            if i < len(messages):
                formatted.append("-" * 50)
                formatted.append("")
        
        return "\n".join(formatted)

    def _format_summaries(self, summaries: List[Dict]) -> str:
        """Форматирует саммари для промпта"""
        formatted = []
        for i, summary in enumerate(summaries, 1):
            # Форматируем время
            timestamp = summary['created_at'].strftime("%Y-%m-%d %H:%M:%S") if summary.get('created_at') else "Unknown time"
            
            # Добавляем саммари с номером и временем
            formatted.append(f"=== Summary #{i} ({timestamp}) ===")
            formatted.append(summary['summary_text'])
            formatted.append("")  # Пустая строка для разделения
            
        return "\n".join(formatted)

class SummaryManager:
    def __init__(self):
        self.summarizer = DialogSummarizer()
        
    async def check_and_create_summaries(self, telegram_id: int):
        """Проверяет необходимость создания новых саммари"""
        try:
            logger.info(f"Checking summaries for telegram_id {telegram_id}")
            
            # Получаем user_id из telegram_id
            with get_db() as db:
                user = db.query(User).filter_by(telegram_id=telegram_id).first()
                if not user:
                    logger.error(f"User with telegram_id {telegram_id} not found")
                    return
                user_id = user.id
                logger.info(f"Found user_id {user_id} for telegram_id {telegram_id}")
            
            # Проверяем необходимость Level 1 саммари
            messages = await self._get_unsummarized_messages(user_id)
            logger.info(f"Found {len(messages)} unsummarized messages (threshold: {self.summarizer.messages_threshold})")
            
            # Если достаточно сообщений для саммари первого уровня
            if len(messages) >= self.summarizer.messages_threshold:
                # Берем только первые messages_threshold сообщений
                messages_to_summarize = messages[:self.summarizer.messages_threshold]
                logger.info(f"Creating level 1 summary for {len(messages_to_summarize)} messages")
                
                # Логируем сообщения для отладки
                for msg in messages_to_summarize:
                    logger.info(f"Message {msg['id']}: {msg['message'][:50]}...")
                    logger.info(f"Bot ({msg['character_mode']}): {msg['response'][:50]}...")
                
                # Создаем саммари
                summary = await self.summarizer.create_summary(messages_to_summarize, level=1)
                if summary:
                    logger.info(f"Raw LLM response:\n{summary}")
                    logger.info(f"Cleaned summary:\n{summary}")
                    logger.info("Level 1 summary created successfully")
                    
                    # Сохраняем саммари
                    await self._save_summary(summary, messages_to_summarize, level=1)
                    logger.info("Level 1 summary saved to database")
                    logger.info(f"Summary text: {summary}")
                
            # Проверяем необходимость Level 2 саммари
            l1_summaries = await self._get_level1_summaries(user_id)
            logger.info(f"Found {len(l1_summaries)} level 1 summaries (threshold: {self.summarizer.summaries_threshold})")
            
            # Если достаточно саммари первого уровня
            if len(l1_summaries) >= self.summarizer.summaries_threshold:
                logger.info(f"Creating level 2 summary for {len(l1_summaries)} summaries")
                
                # Создаем саммари второго уровня
                l2_summary = await self.summarizer.create_summary(l1_summaries, level=2)
                if l2_summary:
                    logger.info(f"Raw LLM response:\n{l2_summary}")
                    logger.info(f"Cleaned summary:\n{l2_summary}")
                    logger.info("Level 2 summary created successfully")
                    
                    # Сохраняем саммари
                    await self._save_summary(l2_summary, l1_summaries, level=2)
                    logger.info("Level 2 summary saved to database")
                    logger.info(f"Summary text: {l2_summary}")
        
        except Exception as e:
            logger.error(f"Error in check_and_create_summaries: {e}", exc_info=True)

    async def _get_unsummarized_messages(self, user_id: int) -> List[Dict]:
        """Получает сообщения, которые еще не были суммаризированы"""
        with get_db() as db:
            # Получаем последний summary для определения точки отсчета
            last_summary = db.query(DialogSummary).filter(
                DialogSummary.user_id == user_id,
                DialogSummary.level == 1
            ).order_by(DialogSummary.end_message_id.desc()).first()
            
            # Получаем новые сообщения после последнего саммари
            query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
            
            if last_summary:
                logger.info(f"Found last summary with end_message_id={last_summary.end_message_id}")
                query = query.filter(ChatHistory.id > last_summary.end_message_id)
            else:
                logger.info("No previous summary found")
                
            messages = query.order_by(ChatHistory.id.asc()).all()
            logger.info(f"Found {len(messages)} messages to summarize")
            
            # Логируем сообщения для отладки
            for msg in messages[:5]:  # Показываем только первые 5 для краткости
                logger.info(f"Message {msg.id}: {msg.message[:50]}...")
            
            result = []
            for m in messages:
                msg_dict = {
                    'id': m.id,
                    'user_id': user_id,
                    'message': m.message,
                    'response': m.response,
                    'timestamp': m.timestamp,
                    'character_mode': m.character_mode
                }
                result.append(msg_dict)
                logger.info(f"Added message to summary:")
                logger.info(f"  ID: {m.id}")
                logger.info(f"  User: {m.message[:100]}...")
                logger.info(f"  Bot ({m.character_mode}): {m.response[:100]}...")
            return result

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
        try:
            with get_db() as db:
                # Получаем первое и последнее сообщение для определения диапазона
                start_msg = messages[0]
                end_msg = messages[-1]
                
                # Для саммари второго уровня используем другой формат
                if level == 2:
                    start_msg_id = start_msg.get('start_message_id', start_msg.get('id'))
                    end_msg_id = end_msg.get('end_message_id', end_msg.get('id'))
                    user_id = start_msg.get('user_id')
                else:
                    start_msg_id = start_msg['id']
                    end_msg_id = end_msg['id']
                    user_id = start_msg['user_id']
                
                logger.info(f"Saving level={level} summary")
                logger.info(f"Start message ID: {start_msg_id}")
                logger.info(f"End message ID: {end_msg_id}")
                logger.info(f"User ID: {user_id}")
                
                summary = DialogSummary(
                    user_id=user_id,
                    summary_text=summary_text,
                    start_message_id=start_msg_id,
                    end_message_id=end_msg_id,
                    level=level
                )
                db.add(summary)
                db.commit()
                
                logger.info(f"Summary saved successfully")
                logger.info(f"Summary text: {summary_text[:200]}...")
                
                # Логируем основные части саммари
                if "Темы:" in summary_text:
                    logger.info("Found topics section")
                if "О пользователе:" in summary_text:
                    logger.info("Found user info section")
                if "Эмоции:" in summary_text:
                    logger.info("Found emotions section")
                if "Незавершенное:" in summary_text:
                    logger.info("Found unfinished section")
                
        except Exception as e:
            logger.error(f"Error saving summary: {e}", exc_info=True)