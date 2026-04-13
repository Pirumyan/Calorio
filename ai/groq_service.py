import logging
import os
import json
import asyncio
from typing import Union, Dict, Any, Optional
from groq import AsyncGroq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# Настройка клиента
groq_client = None
if GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Модели
STT_MODEL = "whisper-large-v3"
LLM_MODEL = "llama-3.3-70b-versatile"

async def transcribe_audio(file_path: str) -> Optional[str]:
    """Транскрибация аудио в текст через Groq Whisper"""
    if not groq_client:
        return None
        
    try:
        with open(file_path, "rb") as file:
            translation = await groq_client.audio.transcriptions.create(
                file=(os.path.basename(file_path), file.read()),
                model=STT_MODEL,
                response_format="text",
            )
            return translation
    except Exception as e:
        logger.error(f"Groq STT error: {e}")
        return None

async def groq_chat_completion(prompt: str, system_instruction: str, temperature: float = 0.0) -> Optional[str]:
    """Генерация ответа через Groq LLM"""
    if not groq_client:
        return None
        
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            model=LLM_MODEL,
            temperature=temperature,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq LLM error: {e}")
        return None

async def analyze_food_groq(text: str, language: str, system_instruction: str) -> Dict[str, Any]:
    """Анализ еды через Groq (только текст)"""
    response_text = await groq_chat_completion(text, system_instruction)
    if not response_text:
        return {"error": "Groq analysis failed"}
        
    try:
        # Чистка markdown если есть
        json_text = response_text.strip()
        if json_text.startswith("```json"): json_text = json_text[7:]
        elif json_text.startswith("```"): json_text = json_text[3:]
        if json_text.endswith("```"): json_text = json_text[:-3]
        
        data = json.loads(json_text.strip())
        return {
            "foods": data.get("foods", []),
            "calories": data.get("calories"),
            "proteins": data.get("proteins"),
            "fats": data.get("fats"),
            "carbs": data.get("carbs"),
            "analysis": data.get("analysis", "")
        }
    except Exception as e:
        logger.error(f"Groq JSON parse error: {e}")
        return {"error": "Failed to parse Groq response"}

async def analyze_diary_groq(text: str, language: str, system_instruction: str) -> Dict[str, Any]:
    """Анализ дневника через Groq (только текст)"""
    response_text = await groq_chat_completion(text, system_instruction)
    if not response_text:
        return {"error": "Groq diary analysis failed"}
        
    try:
        json_text = response_text.strip()
        if json_text.startswith("```json"): json_text = json_text[7:]
        elif json_text.startswith("```"): json_text = json_text[3:]
        if json_text.endswith("```"): json_text = json_text[:-3]
        
        return json.loads(json_text.strip())
    except Exception as e:
        logger.error(f"Groq Diary JSON parse error: {e}")
        return {"error": "Failed to parse Groq diary response"}
