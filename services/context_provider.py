import logging
from typing import Optional
from database import get_db
from models.user import User
from models.dialog_summary import DialogSummary
from models.chat_history import ChatHistory
from services.summarization import SummaryManager

logger = logging.getLogger(__name__)

class SummaryContextProvider:
    def __init__(self):
        self.summary_manager = SummaryManager()
        self.recent_messages_limit = 20
        self.context_cache = {}  # Кэш для хранения контекста по user_id
        
    async def load_last_context(self, user_id: int) -> str:
        """Загружает последний доступный контекст для пользователя"""
        try:
            logger.info(f"Loading last context for user {user_id}")
            with get_db() as db:
                user = db.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return ""
                
                # Получаем все необходимые данные внутри сессии
                summaries = list(user.summaries)  # Преобразуем в список до закрытия сессии
                chat_history = list(user.chat_history)  # Получаем всю историю
                recent_messages = list(user.get_recent_dialogs(5))  # Берем только последние 5 сообщений
                current_mode = user.character_mode or 'default'
                
                logger.info(f"Found user {user.id} with {len(summaries)} summaries and {len(chat_history)} messages")
                
                # Пробуем получить последний L2 саммари
                l2_summaries = [s for s in summaries if s.level == 2]
                if l2_summaries:
                    l2_summary = max(l2_summaries, key=lambda x: x.created_at)
                    logger.info(f"Found L2 summary: {l2_summary.summary_text[:100]}...")
                    self.context_cache[user_id] = l2_summary.summary_text
                    return l2_summary.summary_text
                else:
                    logger.info("No L2 summaries found")
                
                # Если нет L2, берем последние L1
                l1_summaries = [s for s in summaries if s.level == 1]
                l1_summaries.sort(key=lambda x: x.created_at, reverse=True)
                l1_summaries = l1_summaries[:3]  # Берем только последние 3
                if l1_summaries:
                    logger.info(f"Found {len(l1_summaries)} L1 summaries")
                    for i, s in enumerate(l1_summaries):
                        logger.info(f"Summary {i+1}: {s.summary_text[:100]}...")
                    combined = self._combine_summaries(l1_summaries)
                    self.context_cache[user_id] = combined
                    return combined
                else:
                    logger.info("No L1 summaries found")
                
                # Если нет саммари, берем последние сообщения
                if recent_messages:
                    logger.info(f"Found {len(recent_messages)} recent messages")
                    for i, msg in enumerate(recent_messages):
                        logger.info(f"Message {i+1}: {msg.message[:50]}... -> {msg.response[:50]}...")
                    formatted_text = self._format_dialog_history(recent_messages)
                    self.context_cache[user_id] = formatted_text
                    return formatted_text
                else:
                    logger.info("No messages found")
                
                logger.info("No context available")
                return ""
                
        except Exception as e:
            logger.error(f"Error loading last context: {e}", exc_info=True)
            logger.error("Stack trace:", exc_info=True)
            return ""
            
    def _get_last_summary(self, user: User, level: int):
        """Получает последний саммари указанного уровня"""
        from sqlalchemy import desc
        summaries = [s for s in user.summaries if s.level == level]
        if not summaries:
            return None
        return max(summaries, key=lambda x: x.created_at)
    
    def _get_last_summaries(self, user: User, level: int, limit: int):
        """Получает последние саммари указанного уровня"""
        summaries = [s for s in user.summaries if s.level == level]
        summaries.sort(key=lambda x: x.created_at, reverse=True)
        return summaries[:limit]
    
    def _combine_summaries(self, summaries: list) -> str:
        """Объединяет несколько саммари в один текст"""
        if not summaries:
            return ""
        
        parts = []
        for i, summary in enumerate(summaries, 1):
            parts.append(f"=== Саммари #{i} ===")
            if hasattr(summary, 'summary_text'):
                parts.append(summary.summary_text)
            else:
                parts.append(str(summary))
            parts.append("")  # Пустая строка для разделения
            
        result = "\n".join(parts)
        logger.info(f"Combined {len(summaries)} summaries, total length: {len(result)}")
        return result
        
    def _format_dialog_history(self, messages: list, include_stats: bool = True) -> str:
        """Форматирует историю диалога"""
        if not messages:
            return "История диалога пока пуста."
            
        formatted = []
        formatted.append("📝 Последние сообщения:")
        
        # Добавляем сообщения
        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            formatted.append(f"[{timestamp}] User: {msg.message}")
            formatted.append(f"[{timestamp}] Assistant ({msg.character_mode}): {msg.response}")
            formatted.append("-" * 40)
        
        return "\n".join(formatted)

    def _get_dialog_stats(self, messages: list, summaries: list, current_mode: str) -> str:
        """Формирует статистику диалога"""
        if not messages:
            return "📊 Статистика:\n• История диалога пока пуста"
            
        stats = []
        stats.append("📊 Статистика диалога:")
        stats.append(f"• Всего сообщений: {len(messages)}")
        stats.append(f"• Создано саммари: {len(summaries)}")
        
        # Добавляем информацию о режимах
        modes = set(msg.character_mode for msg in messages)
        stats.append(f"• Использовано режимов: {len(modes)}")
        if modes:
            stats.append(f"• Режимы: {', '.join(modes)}")
        stats.append(f"• Текущий режим: {current_mode}")
        
        # Добавляем временные рамки
        if messages:
            first_msg = min(messages, key=lambda x: x.timestamp)
            last_msg = max(messages, key=lambda x: x.timestamp)
            stats.append(f"• Первое сообщение: {first_msg.timestamp.strftime('%d.%m.%Y %H:%M')}")
            stats.append(f"• Последнее сообщение: {last_msg.timestamp.strftime('%d.%m.%Y %H:%M')}")
        
        return "\n".join(stats)

    async def extract_user_profile_from_history(self, user_id: int) -> dict:
        """Извлекает информацию о пользователе из истории диалогов с помощью LLM"""
        try:
            with get_db() as db:
                user = db.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    return {}
                
                # Получаем всю историю диалогов
                chat_history = list(user.chat_history)
                if not chat_history:
                    return {}
                
                # Форматируем диалоги для анализа
                dialog_text = []
                for msg in chat_history:
                    dialog_text.append(f"User: {msg.message}")
                    dialog_text.append(f"Assistant: {msg.response}")
                    dialog_text.append("-" * 40)
                
                # Создаем промпт для LLM
                prompt = f"""Проанализируй следующий диалог и извлеки информацию о пользователе.
Диалог:
{chr(10).join(dialog_text)}

Извлеки следующую информацию в формате JSON:
1. name - имя пользователя
2. age - возраст (число)
3. occupation - род занятий/профессия
4. interests - интересы и увлечения
5. character - черты характера, которые проявились в диалоге
6. communication_style - стиль общения

Формат ответа:
{{
    "name": "имя или null если не найдено",
    "age": число или null если не найдено,
    "occupation": "профессия или null если не найдено",
    "interests": ["интерес1", "интерес2"] или [] если не найдено,
    "character": ["черта1", "черта2"] или [] если не найдено,
    "communication_style": ["стиль1", "стиль2"] или [] если не найдено
}}
"""
                from llm_integration import llm_manager
                import json

                # Вызываем LLM API
                try:
                    response = await llm_manager.get_response(prompt)
                    # Пытаемся распарсить JSON из ответа
                    try:
                        profile_data = json.loads(response)
                        # Обновляем информацию о пользователе в базе данных
                        if profile_data.get('name'):
                            user.update_user_info('name', profile_data['name'])
                        if profile_data.get('age'):
                            user.update_user_info('age', str(profile_data['age']))
                        if profile_data.get('occupation'):
                            user.update_user_info('occupation', profile_data['occupation'])
                        if profile_data.get('interests'):
                            user.update_user_info('interests', ', '.join(profile_data['interests']))
                        if profile_data.get('character'):
                            user.update_user_info('character_traits', ', '.join(profile_data['character']))
                        if profile_data.get('communication_style'):
                            user.update_user_info('communication_style', ', '.join(profile_data['communication_style']))
                        db.commit()
                        return profile_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing LLM response as JSON: {e}")
                        logger.error(f"Raw response: {response}")
                        return {}
                except Exception as e:
                    logger.error(f"Error getting LLM response: {e}")
                    return {}
                
        except Exception as e:
            logger.error(f"Error extracting user profile from history: {e}")
            return {}

    async def get_context(self, message: str, user_id: int) -> str:
        """
        Формирует контекст для ответа, используя:
        1. Кэшированный контекст или последний саммари
        2. Последние N сообщений
        3. Текущий режим характера
        4. Информацию о пользователе
        """
        try:
            # Сначала проверяем необходимость создания новых саммари
            logger.info(f"Checking for new summaries for user {user_id}")
            await self.summary_manager.check_and_create_summaries(user_id)
            
            with get_db() as db:
                user = db.query(User).filter_by(telegram_id=user_id).first()
                if not user:
                    return ""
                
                # Если нет кэшированного контекста, загружаем его
                if user_id not in self.context_cache:
                    logger.info("No cached context found, loading last context")
                    await self.load_last_context(user_id)
                
                # Получаем кэшированный контекст
                cached_context = self.context_cache.get(user_id, "История диалога пока пуста.")
                logger.info(f"Using cached context, length: {len(cached_context)}")
                
                # Получаем все необходимые данные внутри сессии
                chat_history = list(db.query(ChatHistory).filter_by(user_id=user.id).all())
                recent_messages = sorted(chat_history, key=lambda x: x.timestamp, reverse=True)[:5]
                summaries = list(db.query(DialogSummary).filter_by(user_id=user.id).all())
                current_mode = user.character_mode or 'default'
                user_profile = user.get_user_profile()
                
                # Форматируем последние сообщения и статистику
                logger.info("Getting recent messages and stats")
                recent_messages_text = self._format_dialog_history(recent_messages)
                stats_text = self._get_dialog_stats(chat_history, summaries, current_mode)
                
                logger.info(f"Current character mode: {current_mode}")
                logger.info(f"User profile: {user_profile}")

                # Формируем полный контекст
                context_parts = [
                    "=== ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ ===",
                    user_profile,
                    "\n=== СТАТИСТИКА ДИАЛОГА ===",
                    stats_text,
                    "\n=== ИСТОРИЯ ДИАЛОГОВ ===",
                    cached_context,
                    "\n=== ПОСЛЕДНИЙ КОНТЕКСТ ===",
                    recent_messages_text,
                    "\n=== ТЕКУЩЕЕ СООБЩЕНИЕ ===",
                    f"User: {message}"
                ]

                result = "\n".join(filter(None, context_parts))
                logger.info(f"Generated context, length: {len(result)}")
                return result

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return ""