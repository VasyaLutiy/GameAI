"""LLM integration module"""
import aiohttp
from typing import Optional, Dict
from config.settings import LLM_API_BASE, LLM_MODEL_NAME, MAX_TOKENS

class LLMManager:
    def __init__(self):
        self.api_base = LLM_API_BASE
        self.model = LLM_MODEL_NAME
        self.max_tokens = MAX_TOKENS

    async def get_response(self, message: str, system_prompt: str = None) -> str:
        """Get response from LLM model"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        return f"API Error: {response.status} - {error_text}"
            except Exception as e:
                return f"Error calling LLM: {str(e)}"

llm_manager = LLMManager()