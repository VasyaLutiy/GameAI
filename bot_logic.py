import logging
from typing import Optional
from llm_integration import llm_manager
from services.context_provider import SummaryContextProvider

logger = logging.getLogger(__name__)

class VasilisaBot:
    def __init__(self, character_mode="default"):
        self.character_mode = character_mode
        self._context_provider = None
        self.load_character_data()
        
    @property
    def context_provider(self):
        if self._context_provider is None:
            self._context_provider = SummaryContextProvider()
        return self._context_provider
    
    @context_provider.setter
    def context_provider(self, value):
        if isinstance(value, str):
            self._context_provider = SummaryContextProvider()
        else:
            self._context_provider = value
        
    def load_character_data(self):
        """Загрузка данных персонажа"""
        import json
        with open('character_profiles.json', 'r', encoding='utf-8') as f:
            self.character_profiles = json.load(f)
        self.current_profile = self.character_profiles[self.character_mode]
    
    def switch_character(self, mode: str):
        """Переключение между характерами"""
        # Перезагружаем профили на случай изменений в файле
        self.load_character_data()
        
        if mode in self.character_profiles:
            self.character_mode = mode
            self.current_profile = self.character_profiles[mode]
            logger.info(f"Character switched to: {mode} ({self.current_profile['name']})")
            return f"Характер изменен на: {self.current_profile['name']}"
        else:
            available_modes = ', '.join(self.character_profiles.keys())
            logger.warning(f"Invalid character mode requested: {mode}. Available: {available_modes}")
            return f"Ошибка: характер '{mode}' не найден.\nДоступные режимы: {available_modes}"
            
    async def create_system_prompt(self, message: str = "", user_id: int = None) -> str:
        """Создание системного промпта на основе данных персонажа"""
        profile = self.current_profile['personality']
        traits = ', '.join(profile['traits'])
        speech_style = ', '.join(profile['speech_style'])
        
        # Получаем контекст диалога
        dialog_context = await self.context_provider.get_context(message, user_id) if user_id else ""
        
        base_prompt = profile['system_prompt']
        
        return f"""{base_prompt}

Твои черты характера: {traits}
Твой стиль речи: {speech_style}

История диалога:
{dialog_context}

Помни: ты {self.current_profile['name']}, сохраняй свой уникальный стиль общения."""
        
    async def get_response(self, message: str, user_id: int = None) -> str:
        """Получение ответа от модели"""
        try:
            logger.info(f"get_response called with message='{message}', user_id={user_id}")
            system_prompt = await self.create_system_prompt(message=message, user_id=user_id)
            logger.info(f"Created system prompt, length: {len(system_prompt)}")
            
            response = await llm_manager.get_response(message, system_prompt=system_prompt)
            # Очищаем ответ от технических маркеров
            cleaned_response = response.replace("User:", "").replace("Assistant:", "").strip()
            return cleaned_response
        except Exception as e:
            logger.error(f"Error in get_response: {e}", exc_info=True)
            return f"Ошибка при обработке запроса: {str(e)}"

bot = VasilisaBot()