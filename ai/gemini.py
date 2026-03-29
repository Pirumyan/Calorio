import json
import logging
import tempfile
from typing import Union, Dict, Any
import google.generativeai as genai
from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Настраиваем Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Используем актуальную модель
MODEL_NAME = 'gemini-2.5-flash'


def get_system_instruction(language: str) -> str:
    lang_map = {
        'ru': "Отвечай строго на русском языке. Все элементы массива foods и текст analysis должны быть на русском.",
        'en': "Respond strictly in English. All items in the foods array and the analysis text MUST be in English.",
        'am': "Պատասխանեք խստորեն հայերենով: foods զանգվածի բոլոր տարրերը և analysis տեքստը ՊԵՏՔ Է լինեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке.")

    return f"""Ты - профессиональный диетолог и анализатор питания.
Твоя задача - проанализировать то, что съел пользователь (из текста или голосового ввода).
Оцени примерную калорийность, белки, жиры и углеводы, даже если точных цифр нет.

ОЧЕНЬ ВАЖНО: {lang_prompt}
Значения ключей в JSON (названия еды, текст анализа) ДОЛЖНЫ быть переведены на требуемый язык!

Верни ТОЛЬКО валидный JSON со следующей структурой:
{{
  "foods": ["Блюдо 1", "Блюдо 2"],
  "calories": 1200,
  "proteins": 50,
  "fats": 40,
  "carbs": 150,
  "analysis": "Краткий комментарий диетолога (до 3 предложений)"
}}

НИКАКОГО markdown. Только чистый JSON.
{lang_prompt}
"""


async def analyze_food(
    input_data: Union[str, bytes],
    mime_type: str = "text/plain",
    language: str = 'ru'
) -> Dict[str, Any]:

    if not GOOGLE_API_KEY:
        return {
            "error": "API key not set",
            "analysis": "AI недоступен"
        }

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=get_system_instruction(language),
        generation_config=genai.GenerationConfig(
            temperature=0.0
        )
    )

    try:
        content_parts = []

        # 📌 AUDIO (фикс через upload_file)
        if mime_type == "audio/ogg":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
                temp_audio.write(input_data)
                temp_path = temp_audio.name

            uploaded_file = genai.upload_file(path=temp_path)

            content_parts.append(uploaded_file)
            content_parts.append("Проанализируй этот аудиотрек.")

        # 📌 TEXT
        else:
            content_parts.append(input_data)

        response = await model.generate_content_async(content_parts)

        if not response or not response.text:
            raise ValueError("Empty response from Gemini")

        json_text = response.text.strip()

        # 📌 чистка markdown
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        elif json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]

        data = json.loads(json_text.strip())

        # 📌 безопасный возврат
        return {
            "foods": data.get("foods", []),
            "calories": data.get("calories"),
            "proteins": data.get("proteins"),
            "fats": data.get("fats"),
            "carbs": data.get("carbs"),
            "analysis": data.get("analysis", "")
        }

    except Exception as e:
        logger.error(f"Gemini API error: {e}")

        return {
            "error": "Не удалось проанализировать данные",
            "analysis": "Произошла ошибка при обращении к AI."
        }
    finally:
        try:
            if 'uploaded_file' in locals():
                genai.delete_file(uploaded_file.name)
        except Exception:
            pass

async def generate_meal_plan(user_profile: dict, language: str) -> str:
    if not GOOGLE_API_KEY:
        return "AI недоступен. Проверьте API ключ."
        
    lang_map = {
        'ru': "Отвечай строго на русском языке.",
        'en': "Respond strictly in English.",
        'am': "Պատասխանեք խստորեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке")

    prompt = f"""
Ты профессиональный диетолог. 
Пользователь запрашивает "Мое питание". Предложи 3-4 варианта блюд (завтрак, обед, ужин, перекус) на основе его профиля:
Возраст: {user_profile.get('age')}
Вес: {user_profile.get('weight')} кг
Рост: {user_profile.get('height')} см
Цель: {user_profile.get('goal')}

Напиши короткий, приятный и мотивирующий ответ, включающий список рекомендуемых блюд с примерной калорийностью. Не пиши слишком длинно, уложись в 10-15 предложений.
{lang_prompt}
"""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=genai.GenerationConfig(temperature=0.7)
    )
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Meal Plan error: {e}")
        return "Произошла ошибка при генерации плана питания."