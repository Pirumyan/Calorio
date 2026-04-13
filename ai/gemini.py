import json
import logging
import tempfile
import asyncio
from typing import Union, Dict, Any
import google.generativeai as genai
from config import GOOGLE_API_KEY, GROQ_API_KEY
from ai.groq_service import (
    transcribe_audio, groq_chat_completion, 
    analyze_food_groq, analyze_diary_groq
)

logger = logging.getLogger(__name__)

# Настраиваем Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Используем актуальную модель
MODEL_NAME = 'gemini-2.5-flash'


async def _execute_with_retry(func, max_retries: int = 3, base_delay: float = 2.0):
    """
    Вспомогательная функция для повторных попыток при ошибках квоты (429).
    """
    import random
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str or "Resource has been exhausted" in err_str:
                if attempt < max_retries - 1:
                    # Экспоненциальная задержка: 2, 4, 8... секунд + случайный шум
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Gemini Quota Exceeded (429). Retry {attempt + 1}/{max_retries} in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                    continue
            # Если это не 429 или попытки закончились, пробрасываем ошибку дальше
            raise e


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

def get_diary_instruction(language: str) -> str:
    lang_map = {
        'ru': "Отвечай строго на русском языке.",
        'en': "Respond strictly in English.",
        'am': "Պատասխանեք խստորեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке.")

    return f"""Ты - персональный диетолог и фитнес-помощник.
Пользователь присылает тебе "Дневник за день" (текстом или голосом). 
Твоя задача - вытащить из него ВСЮ полезную информацию и вернуть её в формате JSON.

Информация, которую нужно извлечь:
1. Съеденная еда (названия, калории, БЖУ).
2. Выпитая вода (в мл).
3. Физическая активность (название и сожженные калории).
4. Обновления холодильника (что купил - добавить, что закончилось - удалить).
5. Краткий анализ дня и совет.

Верни ТОЛЬКО валидный JSON со следующей структурой:
{{
  "foods": [
    {{"name": "яичница", "calories": 200, "proteins": 15, "fats": 12, "carbs": 2}}
  ],
  "water": 500,
  "exercises": [
    {{"name": "бег 20 мин", "calories_burned": 250}}
  ],
  "fridge_add": ["помидоры", "молоко"],
  "fridge_remove": ["лук"],
  "analysis": "Отличное начало дня! Но постарайся пить больше воды вечером."
}}

ОЧЕНЬ ВАЖНО: {lang_prompt}
Если какая-то информация отсутствует (например, не было спорта), верни пустой список или 0.

НИКАКОГО markdown. Только чистый JSON.
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

    async def _call():
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=get_system_instruction(language),
            generation_config=genai.GenerationConfig(
                temperature=0.0
            )
        )
        content_parts = []
        uploaded_file = None

        if mime_type == "audio/ogg":
            uploaded_file = await asyncio.to_thread(genai.upload_file, path=input_data)
            content_parts.append(uploaded_file)
            content_parts.append("Проанализируй этот аудиотрек.")
        else:
            content_parts.append(input_data)

        try:
            response = await model.generate_content_async(content_parts)
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
            return response.text, uploaded_file
        except Exception as e:
            if uploaded_file:
                await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            raise e

    try:
        response_text, uploaded_file = await _execute_with_retry(_call)
        json_text = response_text.strip()

        # 📌 чистка markdown
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        elif json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]

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
        logger.error(f"Gemini API error after retries: {e}")
        
        # 🛡️ Fallback to Groq
        if GROQ_API_KEY:
            logger.info("Attempting fallback to Groq for analyze_food...")
            text_to_analyze = input_data
            if mime_type == "audio/ogg":
                text_to_analyze = await transcribe_audio(input_data)
                if not text_to_analyze:
                    return {"error": "Groq STT failed", "analysis": "Ошибка транскрибации (Groq)."}
            
            groq_data = await analyze_food_groq(text_to_analyze, language, get_system_instruction(language))
            if "error" not in groq_data:
                # Добавляем пометку, что это ответ от Groq
                groq_data["analysis"] = f"🤖 (Groq) {groq_data.get('analysis', '')}"
                return groq_data

        return {
            "error": "Не удалось проанализировать данные",
            "analysis": "Произошла ошибка при обращении к AI. Возможно, превышен лимит."
        }
    finally:
        if 'uploaded_file' in locals() and uploaded_file:
            try:
                await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            except Exception as e:
                logger.error(f"Error deleting file from Gemini: {e}")

async def analyze_diary_entry(
    input_data: Union[str, bytes],
    mime_type: str = "text/plain",
    language: str = 'ru'
) -> Dict[str, Any]:

    if not GOOGLE_API_KEY:
        return {"error": "API key not set"}

    async def _call():
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=get_diary_instruction(language),
            generation_config=genai.GenerationConfig(temperature=0.0)
        )
        content_parts = []
        uploaded_file = None
        if mime_type == "audio/ogg":
            uploaded_file = await asyncio.to_thread(genai.upload_file, path=input_data)
            content_parts.append(uploaded_file)
            content_parts.append("Проанализируй дневник из аудио.")
        else:
            content_parts.append(f"Проанализируй этот дневник: {input_data}")

        try:
            response = await model.generate_content_async(content_parts)
            return response.text, uploaded_file
        except Exception as e:
            if uploaded_file:
                await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            raise e

    try:
        json_text, uploaded_file = await _execute_with_retry(_call)
        json_text = json_text.strip()
        
        if json_text.startswith("```json"): json_text = json_text[7:]
        elif json_text.startswith("```"): json_text = json_text[3:]
        if json_text.endswith("```"): json_text = json_text[:-3]

        return json.loads(json_text.strip())

    except Exception as e:
        logger.error(f"Gemini Diary error after retries: {e}")
        
        # 🛡️ Fallback to Groq
        if GROQ_API_KEY:
            logger.info("Attempting fallback to Groq for analyze_diary_entry...")
            text_to_analyze = input_data
            if mime_type == "audio/ogg":
                text_to_analyze = await transcribe_audio(input_data)
                if not text_to_analyze:
                    return {"error": "Groq STT failed"}
            
            return await analyze_diary_groq(text_to_analyze, language, get_diary_instruction(language))

        return {"error": "Ошибка анализа дневника. Превышен лимит?"}
    finally:
        if 'uploaded_file' in locals() and uploaded_file:
            try: 
                await asyncio.to_thread(genai.delete_file, uploaded_file.name)
            except Exception as e:
                logger.error(f"Error deleting diary file from Gemini: {e}")

async def generate_meal_plan(user_profile: dict, language: str, recent_foods: list[str] = None, is_regenerate: bool = False) -> str:
    if not GOOGLE_API_KEY:
        return "AI недоступен. Проверьте API ключ."
        
    lang_map = {
        'ru': "Отвечай строго на русском языке.",
        'en': "Respond strictly in English.",
        'am': "Պատասխանեք խստորեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке")

    foods_context = ""
    if recent_foods:
        foods_text = ", ".join(recent_foods)
        foods_context = f"\nПользователь ранее ел и любит: {foods_text}. Обязательно учитывай эти предпочтения при составлении нового меню!"

    regen_context = ""
    if is_regenerate:
        regen_context = "\nВАЖНО: Пользователь попросил предложить ДРУГОЕ меню. Сгенерируй новые блюда, отличные от предыдущих, но с учетом его любимой еды."

    prompt = f"""
Ты профессиональный диетолог. 
Пользователь запрашивает "Мое питание". Предложи 3-4 варианта блюд (завтрак, обед, ужин, перекус) на основе его профиля:
Возраст: {user_profile.get('age')}
Вес: {user_profile.get('weight')} кг
Рост: {user_profile.get('height')} см
Цель: {user_profile.get('goal')}
{foods_context}
{regen_context}

Напиши короткий, приятный и мотивирующий ответ, включающий список рекомендуемых блюд с примерной калорийностью. Не пиши слишком длинно, уложись в 10-15 предложений.
{lang_prompt}
"""
    temp = 0.85 if is_regenerate else 0.7
    
    async def _call():
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=temp)
        )
        response = await model.generate_content_async(prompt)
        return response.text

    try:
        return await _execute_with_retry(_call)
    except Exception as e:
        logger.error(f"Gemini Meal Plan error after retries: {e}")
        
        # 🛡️ Fallback to Groq
        if GROQ_API_KEY:
            logger.info("Attempting fallback to Groq for generate_meal_plan...")
            response = await groq_chat_completion(prompt, "You are a professional nutritionist.")
            if response:
                return f"🤖 (Groq)\n{response}"

        return "Произошла ошибка при генерации плана питания. Возможно, превышен лимит запросов, попробуйте позже."


async def generate_fridge_recipe(ingredients: str, user_profile: dict, norms: dict, language: str) -> str:
    if not GOOGLE_API_KEY:
        return "AI недоступен. Проверьте API ключ."
        
    lang_map = {
        'ru': "Отвечай строго на русском языке.",
        'en': "Respond strictly in English.",
        'am': "Պատասխանեք խստորեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке")

    prompt = f"""
Ты профессиональный шеф-повар и диетолог. 
У пользователя есть следующие продукты в холодильнике: {ingredients}.
Его дневная норма калорий: ~{norms.get('calories')} ккал. Цель: {user_profile.get('goal')}.

Предложи 1 здоровый и вкусный рецепт из этих ингредиентов (можно добавить базу: соль, масло, специи).
Укажи КБЖУ получившегося блюда и пошаговый рецепт.
{lang_prompt}
"""
    async def _call():
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.7)
        )
        response = await model.generate_content_async(prompt)
        return response.text

    try:
        return await _execute_with_retry(_call)
    except Exception as e:
        logger.error(f"Gemini Fridge Recipe error after retries: {e}")
        
        # 🛡️ Fallback to Groq
        if GROQ_API_KEY:
            logger.info("Attempting fallback to Groq for generate_fridge_recipe...")
            response = await groq_chat_completion(prompt, "You are a chef and nutritionist.")
            if response:
                return f"🤖 (Groq)\n{response}"

        return "Произошла ошибка при генерации рецепта. Возможно, превышен лимит запросов."

async def analyze_day_summary(stats: dict, norms: dict, foods: list[str], user_profile: dict, language: str) -> str:
    if not GOOGLE_API_KEY:
        return "AI недоступен."
        
    lang_map = {
        'ru': "Отвечай строго на русском языке.",
        'en': "Respond strictly in English.",
        'am': "Պատասխանեք խստորեն հայերենով:"
    }
    lang_prompt = lang_map.get(language, "Отвечай на русском языке")

    foods_str = ", ".join(foods) if foods else "Данных о еде нет"
    
    prompt = f"""
Ты профессиональный диетолог. Проанализируй данные пользователя за сегодня и дай ОДИН короткий совет (до 3 предложений).
Данные за сегодня:
- Потреблено: {stats['calories']} / {norms['calories']} ккал
- Белки: {stats['proteins']} / {norms['proteins']} г
- Жиры: {stats['fats']} / {norms['fats']} г
- Углеводы: {stats['carbs']} / {norms['carbs']} г
- Вода: {stats['water']} / {norms['water']} мл
- Список съеденного сегодня: {foods_str}

Профиль пользователя:
- Цель: {user_profile.get('goal')}
- Рост/Вес/Возраст: {user_profile.get('height')}/{user_profile.get('weight')}/{user_profile.get('age')}

Дай краткую оценку дня и практический совет, как улучшить питание или активность.
{lang_prompt}
"""
    async def _call():
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.7)
        )
        response = await model.generate_content_async(prompt)
        return response.text

    try:
        return await _execute_with_retry(_call)
    except Exception as e:
        logger.error(f"Gemini Day Summary error after retries: {e}")
        
        # 🛡️ Fallback to Groq
        if GROQ_API_KEY:
            logger.info("Attempting fallback to Groq for analyze_day_summary...")
            response = await groq_chat_completion(prompt, "You are a professional nutritionist.")
            if response:
                return f"🤖 (Groq) {response}"

        return "Ошибка при анализе дня. Попробуйте позже."