import json
import pytest
import aiohttp
from typing import Optional, Dict

import os
from dotenv import load_dotenv

# Загружаем настройки из .env
load_dotenv()

class VasilisaLLM:
    def __init__(self, character_mode="default", context_provider="simple_json"):
        self.api_base = os.getenv('LLM_API_BASE')
        self.model = os.getenv('LLM_MODEL_NAME')
        self.max_tokens = 4096
        self.character_mode = character_mode
        self.context_provider = context_provider
        self.load_character_data()
        
    def load_character_data(self):
        """Загрузка данных персонажа и диалогов"""
        # Загружаем базовые диалоги
        with open('dialogs.json', 'r', encoding='utf-8') as f:
            self.dialog_data = json.load(f)
            
        # Загружаем профили характеров
        with open('character_profiles.json', 'r', encoding='utf-8') as f:
            self.character_profiles = json.load(f)
            
        # Устанавливаем текущий профиль
        self.current_profile = self.character_profiles[self.character_mode]
    
    def switch_character(self, mode: str):
        """Переключение между характерами"""
        if mode in self.character_profiles:
            self.character_mode = mode
            self.current_profile = self.character_profiles[mode]
            return f"Характер изменен на: {self.current_profile['name']}"
        else:
            return f"Ошибка: характер '{mode}' не найден. Доступные характеры: {', '.join(self.character_profiles.keys())}"
            
    async def get_context_provider(self, provider_type="simple_json"):
        """Выбор провайдера контекста диалогов"""
        if provider_type == "simple_json":
            return self.simple_json_content
        elif provider_type == "history":
            return self.history_content
        elif provider_type == "combined":
            return self.combined_content
        elif provider_type == "summary":
            return self.summary_content
        else:
            return self.simple_json_content  # default fallback

    async def summary_content(self, message: str, user_id: int = None, num_examples: int = 3) -> str:
        """Провайдер контекста на основе саммари"""
        from services.context_provider import SummaryContextProvider
        
        if not user_id:
            return self.simple_json_content(message, num_examples)
            
        provider = SummaryContextProvider()
        return await provider.get_context(message, user_id)

    def combined_content(self, message: str, user_id: int = None, num_examples: int = 3) -> str:
        """Комбинированный провайдер контекста (базовые диалоги + история)"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Combined content called with message='{message}', user_id={user_id}")
        combined = []
        
        # Получаем базовые примеры
        base_examples = self.simple_json_content(message, num_examples=2)
        if base_examples:
            combined.append("Базовые примеры диалогов:")
            combined.append(base_examples)
        logger.info("Got base examples")
        
        # Получаем историю диалогов, если есть user_id
        if user_id:
            history_examples = self.history_content(message, user_id, num_examples=5)
            if history_examples:
                combined.append("\nВаши предыдущие диалоги:")
                combined.append(history_examples)
            logger.info(f"Got history examples: {history_examples[:200] if history_examples else 'None'}...")
        
        result = "\n".join(combined)
        logger.info(f"Combined content result length: {len(result)}")
        return result

    def simple_json_content(self, message: str = None, num_examples: int = 3) -> str:
        """Простой провайдер контекста на основе JSON"""
        import random
        example_dialogs = random.sample(self.dialog_data['conversations'], num_examples)
        return '\n'.join([
            f"Вопрос: {d['q']}\nОтвет: {d['a']}" for d in example_dialogs
        ])

    def history_content(self, message: str, user_id: int, num_examples: int = 20) -> str:
        """Провайдер контекста на основе истории диалогов"""
        import logging
        logger = logging.getLogger(__name__)
        from dialog_manager import DialogHistoryManager
        
        logger.info(f"Getting history for user_id={user_id}, character_mode={self.character_mode}")
        dialog_manager = DialogHistoryManager()
        
        # Получаем диалоги для текущего характера
        character_dialogs = dialog_manager.get_character_dialogs(
            telegram_id=user_id,
            character_mode=self.character_mode,
            limit=10  # Увеличим лимит
        )
        logger.info(f"Got {len(character_dialogs)} character dialogs")
        for i, d in enumerate(character_dialogs):
            logger.info(f"Dialog {i+1}: {d['message'][:100]} -> {d['response'][:100]}")
        
        # Получаем общие диалоги в любом случае
        recent_dialogs = dialog_manager.get_recent_dialogs(
            telegram_id=user_id,
            limit=10  # Увеличим лимит для общих диалогов
        )
        logger.info(f"Got {len(recent_dialogs)} recent dialogs")
        for i, d in enumerate(recent_dialogs):
            logger.info(f"Recent dialog {i+1}: {d['message'][:100]} -> {d['response'][:100]}")
        
        # Объединяем все диалоги
        all_dialogs = character_dialogs + recent_dialogs
        
        formatted_dialogs = dialog_manager.format_dialogs_for_context(all_dialogs)
        logger.info(f"Formatted dialogs: {formatted_dialogs[:200]}...")
        return formatted_dialogs

    # Заготовка для векторного провайдера
    # def vector_content(self, message: str, num_examples: int = 3) -> str:
    #     """Векторный провайдер контекста"""
    #     # TODO: Реализовать векторный поиск похожих диалогов
    #     pass

    async def create_system_prompt(self, message: str = "", user_id: int = None) -> str:
        """Создание системного промпта на основе данных персонажа"""
        profile = self.current_profile['personality']
        traits = ', '.join(profile['traits'])
        speech_style = ', '.join(profile['speech_style'])
        
        # Получаем примеры диалогов через выбранный провайдер
        provider = await self.get_context_provider(self.context_provider)
        dialog_examples = await provider(message, user_id) if user_id else provider(message)
        
        base_prompt = profile['system_prompt']
        
        return f"""{base_prompt}

Твои черты характера: {traits}
Твой стиль речи: {speech_style}

Вот примеры базовых диалогов (адаптируй их под свой характер):
{dialog_examples}

Помни: ты {self.current_profile['name']}, сохраняй свой уникальный стиль общения."""
        
    async def get_response(self, message: str, user_id: int = None, system_prompt: str = None) -> str:
        """Получение ответа от модели"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"get_response called with message='{message}', user_id={user_id}")
        if system_prompt is None:
            system_prompt = await self.create_system_prompt(message=message, user_id=user_id)
        logger.info(f"Using system prompt, length: {len(system_prompt)}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        "max_tokens": self.max_tokens,
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        return f"Ошибка API: {response.status} - {error_text}"
            except Exception as e:
                return f"Ошибка при обращении к LLM: {str(e)}"

@pytest.mark.asyncio
async def test_vasilia_basic_chat():
    """Тест базового общения с Василисой с разными провайдерами контекста"""
    # Тест с простым JSON провайдером
    vasilia_simple = VasilisaLLM(context_provider="simple_json")
    
    # Тест с дефолтным провайдером (должен быть simple_json)
    vasilia_default = VasilisaLLM()
    
    test_messages = [
        "Здравствуйте! Как вас зовут?",
        "Можете помочь организовать мой день?",
        "У меня много задач, и я не знаю, за что взяться первым делом",
    ]
    
    for message in test_messages:
        print(f"\nТест simple_json провайдера:")
        print(f"Вопрос: {message}")
        response_simple = await vasilia_simple.get_response(message)
        print(f"Ответ Василисы (simple_json): {response_simple}")
        
        print(f"\nТест дефолтного провайдера:")
        response_default = await vasilia_default.get_response(message)
        print(f"Ответ Василисы (default): {response_default}")
        
        # Базовые проверки
        for response in [response_simple, response_default]:
            assert response is not None
            assert len(response) > 0
            assert isinstance(response, str)

@pytest.mark.asyncio
async def test_vasilia_character_consistency():
    """Тест соответствия характеру персонажа с разными провайдерами"""
    vasilia = VasilisaLLM(context_provider="simple_json")
    
    test_scenarios = [
        ("default", "Что делать, если всё валится из рук?", "народная мудрость"),
        ("cyber", "Как оптимизировать рабочий процесс?", "кибер-стиль"),
        ("sassy", "Что думаешь о современной моде?", "дерзкий стиль")
    ]
    
    for character, question, style in test_scenarios:
        vasilia.switch_character(character)
        response = await vasilia.get_response(question)
        print(f"\nХарактер: {character}")
        print(f"Вопрос: {question}")
        print(f"Ответ ({style}): {response}")
        
        # Проверяем, что ответ не пустой
        assert response is not None
        assert len(response) > 0

@pytest.mark.asyncio
async def test_context_provider_switch():
    """Тест переключения провайдеров контекста"""
    vasilia = VasilisaLLM()
    
    # Проверяем, что провайдер по умолчанию работает
    assert vasilia.context_provider == "simple_json"
    
    # Проверяем работу simple_json провайдера
    dialog_examples = vasilia.simple_json_content()
    assert dialog_examples is not None
    assert isinstance(dialog_examples, str)
    assert "Вопрос:" in dialog_examples
    assert "Ответ:" in dialog_examples

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
