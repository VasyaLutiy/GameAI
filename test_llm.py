import os
import pytest
import aiohttp
import json
from typing import Optional, Dict

# Настройки
LLM_API_BASE = 'http://172.18.0.3:4000/v1'
LLM_MODEL_NAME = 'Claude'

class SimpleLLMManager:
    def __init__(self):
        self.api_base = LLM_API_BASE
        self.model = LLM_MODEL_NAME
        self.max_tokens = 4096
        
    async def get_response(self, message: str, system_prompt: str = None) -> str:
        """Получить ответ от модели"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt or "Ты - помощник, отвечай кратко и по существу."},
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
async def test_simple_chat():
    """Простой тест чата"""
    manager = SimpleLLMManager()
    response = await manager.get_response("Привет! Как тебя зовут?")
    print(f"\nОтвет от LLM: {response}")
    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)

@pytest.mark.asyncio
async def test_mood_analysis():
    """Тест анализа настроения текста"""
    manager = SimpleLLMManager()
    system_prompt = """
    Ты - анализатор настроения текста. Проанализируй настроение в сообщении пользователя и верни только JSON с оценками от 0 до 1:
    {
        "positive": 0.0-1.0,
        "negative": 0.0-1.0,
        "neutral": 0.0-1.0
    }
    """
    
    test_messages = [
        "Я очень счастлив сегодня!",
        "Всё ужасно, я расстроен.",
        "Обычный день, ничего особенного."
    ]
    
    for message in test_messages:
        response = await manager.get_response(message, system_prompt)
        print(f"\nТекст: {message}")
        print(f"Анализ настроения: {response}")
        
        # Пробуем распарсить JSON
        try:
            mood = json.loads(response)
            assert isinstance(mood, dict)
            assert "positive" in mood
            assert "negative" in mood
            assert "neutral" in mood
            assert all(isinstance(v, (int, float)) for v in mood.values())
            assert all(0 <= v <= 1 for v in mood.values())
            assert abs(sum(mood.values()) - 1.0) < 0.1  # Сумма должна быть близка к 1
        except json.JSONDecodeError:
            pytest.fail(f"Не удалось распарсить JSON из ответа: {response}")
        except AssertionError:
            pytest.fail(f"Некорректный формат данных в ответе: {response}")

@pytest.mark.asyncio
async def test_error_handling():
    """Тест обработки ошибок и граничных случаев"""
    manager = SimpleLLMManager()
    
    # Тест с очень длинным текстом
    long_text = "очень " * 1000 + "длинный текст"
    response = await manager.get_response(long_text)
    print(f"\nОтвет на длинный текст: {response[:100]}...")
    assert response is not None
    assert len(response) > 0
    
    # Тест с некорректным URL
    manager.api_base = "http://invalid-url:4000/v1"
    response = await manager.get_response("Тестовое сообщение")
    print(f"\nОтвет при неверном URL: {response}")
    assert "Ошибка при обращении к LLM" in response
    
    # Тест с пустым сообщением
    manager.api_base = LLM_API_BASE  # Восстанавливаем правильный URL
    response = await manager.get_response("")
    print(f"\nОтвет на пустое сообщение: {response}")
    assert response is not None
    assert len(response) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
