import json
import pytest
import aiohttp
from typing import Optional, Dict

# Настройки
LLM_API_BASE = 'http://172.17.0.2:4000/v1'
LLM_MODEL_NAME = 'Claude'

class VasilisaLLM:
    def __init__(self, character_mode="default", context_provider="simple_json"):
        self.api_base = LLM_API_BASE
        self.model = LLM_MODEL_NAME
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
            
    def get_context_provider(self, provider_type="simple_json"):
        """Выбор провайдера контекста диалогов"""
        if provider_type == "simple_json":
            return self.simple_json_content
        # Здесь можно добавить другие провайдеры:
        # elif provider_type == "vector":
        #     return self.vector_content
        else:
            return self.simple_json_content  # default fallback

    def simple_json_content(self, message: str = None, num_examples: int = 3) -> str:
        """Простой провайдер контекста на основе JSON"""
        import random
        example_dialogs = random.sample(self.dialog_data['conversations'], num_examples)
        return '\n'.join([
            f"Вопрос: {d['q']}\nОтвет: {d['a']}" for d in example_dialogs
        ])

    # Заготовка для векторного провайдера
    # def vector_content(self, message: str, num_examples: int = 3) -> str:
    #     """Векторный провайдер контекста"""
    #     # TODO: Реализовать векторный поиск похожих диалогов
    #     pass

    def create_system_prompt(self, context_provider="simple_json") -> str:
        """Создание системного промпта на основе данных персонажа"""
        profile = self.current_profile['personality']
        traits = ', '.join(profile['traits'])
        speech_style = ', '.join(profile['speech_style'])
        
        # Получаем примеры диалогов через выбранный провайдер
        provider = self.get_context_provider(context_provider)
        dialog_examples = provider()
        
        base_prompt = profile['system_prompt']
        
        return f"""{base_prompt}

Твои черты характера: {traits}
Твой стиль речи: {speech_style}

Вот примеры базовых диалогов (адаптируй их под свой характер):
{dialog_examples}

Помни: ты {self.current_profile['name']}, сохраняй свой уникальный стиль общения."""
        
    async def get_response(self, message: str) -> str:
        """Получение ответа от модели"""
        system_prompt = self.create_system_prompt(context_provider=self.context_provider)
        
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