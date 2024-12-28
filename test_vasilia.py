import json
import pytest
import aiohttp
from typing import Optional, Dict

# Настройки
LLM_API_BASE = 'http://172.17.0.2:4000/v1'
LLM_MODEL_NAME = 'Claude'

class VasilisaLLM:
    def __init__(self, character_mode="default"):
        self.api_base = LLM_API_BASE
        self.model = LLM_MODEL_NAME
        self.max_tokens = 4096
        self.character_mode = character_mode
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
            
    def create_system_prompt(self) -> str:
        """Создание системного промпта на основе данных персонажа"""
        profile = self.current_profile['personality']
        traits = ', '.join(profile['traits'])
        speech_style = ', '.join(profile['speech_style'])
        
        # Выбираем 3 случайных диалога для примера
        import random
        example_dialogs = random.sample(self.dialog_data['conversations'], 3)
        dialog_examples = '\n'.join([
            f"Вопрос: {d['q']}\nОтвет: {d['a']}" for d in example_dialogs
        ])
        
        base_prompt = profile['system_prompt']
        
        return f"""{base_prompt}

Твои черты характера: {traits}
Твой стиль речи: {speech_style}

Вот примеры базовых диалогов (адаптируй их под свой характер):
{dialog_examples}

Помни: ты {self.current_profile['name']}, сохраняй свой уникальный стиль общения."""
        
    async def get_response(self, message: str) -> str:
        """Получение ответа от модели"""
        system_prompt = self.create_system_prompt()
        
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
    """Тест базового общения с Василисой"""
    vasilia = VasilisaLLM()
    
    test_messages = [
        "Здравствуйте! Как вас зовут?",
        "Можете помочь организовать мой день?",
        "У меня много задач, и я не знаю, за что взяться первым делом",
        "Как справиться со стрессом на работе?",
        "Спасибо за советы! До свидания!"
    ]
    
    for message in test_messages:
        print(f"\nВопрос: {message}")
        response = await vasilia.get_response(message)
        print(f"Ответ Василисы: {response}")
        
        # Базовые проверки
        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)

@pytest.mark.asyncio
async def test_vasilia_character_consistency():
    """Тест соответствия характеру персонажа"""
    vasilia = VasilisaLLM()
    
    # Проверка использования народной мудрости
    response = await vasilia.get_response("Что делать, если всё валится из рук?")
    print(f"\nВопрос о трудностях: {response}")
    
    # Проверка делового совета
    response = await vasilia.get_response("Как лучше организовать важную встречу?")
    print(f"\nВопрос о деловой встрече: {response}")
    
    # Проверка эмпатии
    response = await vasilia.get_response("Я очень волнуюсь перед важным выступлением")
    print(f"\nВопрос о волнении: {response}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])