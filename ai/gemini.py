import json
import logging
from typing import Union, Dict, Any
import google.generativeai as genai
from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Настраиваем Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Используем актуальный Flash для быстрого MVP
MODEL_NAME = 'gemini-2.5-flash' 

def get_system_instruction(language: str) -> str:
    lang_map = {
        'ru': "Отвечай на русском языке.",
        'en': "Respond in English.",
        'am': "Պատասխանեք հայերենով."
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке.")
    
    return f"""Ты - профессиональный диетолог и анализатор питания.
Твоя задача - проанализировать то, что съел пользователь (из текста или голосового ввода).
Оцени примерную калорийность, белки, жиры и углеводы, даже если точных цифр нет.
Верни ТОЛЬКО валидный JSON со следующей структурой:
{{
  "foods": ["Блюдо 1", "Блюдо 2"],
  "calories": 1200,
  "proteins": 50,
  "fats": 40,
  "carbs": 150,
  "analysis": "Краткий комментарий диетолога о приеме пищи (до 3 предложений)"
}}
{lang_prompt}
"""

async def analyze_food(input_data: Union[str, bytes], mime_type: str = "text/plain", language: str = 'ru') -> Dict[str, Any]:
    """
    Универсальная функция для анализа еды через текст или голос.
    input_data - Либо строка текста, либо байты (.ogg)
    mime_type - 'text/plain' или 'audio/ogg'
    """
    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=get_system_instruction(language),
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )

    try:
        content_parts = []
        if mime_type == "audio/ogg":
            content_parts.append({
                "mime_type": "audio/ogg",
                "data": input_data
            })
            content_parts.append("Проанализируй этот аудиотрек.")
        else:
            content_parts.append(input_data)
        
        # Запускаем генерацию асинхронно через run_in_executor или используем generate_content_async (если поддерживается)
        response = await model.generate_content_async(content_parts)
        
        # Получаем текст, он гарантированно JSON из-за response_mime_type
        json_text = response.text
        return json.loads(json_text)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            "error": "Не удалось проанализировать данные",
            "analysis": "Произошла ошибка при обращении к AI."
        }
