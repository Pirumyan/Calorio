import io
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import OnboardingStates
from services.user_service import UserService
from ai.gemini import analyze_food

router = Router()
logger = logging.getLogger(__name__)

# --- ОНБОРДИНГ ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await UserService.get_user(user_id)
    
    if user:
        await message.answer(
            "Привет! Снова рад тебя видеть.\n"
            "Просто напиши или отправь голосовое сообщение о том, что ты съел, "
            "и я все посчитаю и проанализирую!"
        )
    else:
        await message.answer(
            "Добро пожаловать в трекер питания! 🍏\n"
            "Давай познакомимся. Введи свой <b>вес в кг</b> (например, 70):",
            parse_mode="HTML"
        )
        await state.set_state(OnboardingStates.waiting_for_weight)

@router.message(OnboardingStates.waiting_for_weight, F.text)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(weight=weight)
        await message.answer("Отлично. Теперь введи свой <b>рост в см</b> (например, 175):", parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, введи число.")

@router.message(OnboardingStates.waiting_for_height, F.text)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(',', '.'))
        await state.update_data(height=height)
        await message.answer("Теперь укажи свой <b>возраст</b> (полных лет):", parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_age)
    except ValueError:
        await message.answer("Пожалуйста, введи число.")

@router.message(OnboardingStates.waiting_for_age, F.text)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.answer("Какая у тебя <b>цель</b>?\n(например: похудеть, набрать массу, поддержать форму)", parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_goal)
    except ValueError:
        await message.answer("Пожалуйста, введи целое число.")

@router.message(OnboardingStates.waiting_for_goal, F.text)
async def process_goal(message: Message, state: FSMContext):
    goal = message.text
    data = await state.get_data()
    
    # Сохраняем в БД
    lang = UserService.get_user_language(message)
    await UserService.create_user(
        user_id=message.from_user.id,
        weight=data['weight'],
        height=data['height'],
        age=data['age'],
        goal=goal,
        language=lang
    )
    
    await state.clear()
    await message.answer(
        "💪 Профиль сохранен! Теперь ты можешь отправлять мне текст или голосовые сообщения "
        "с описанием своей еды, а я оценю калории и БЖУ."
    )

# --- АНАЛИЗ ЕДЫ ---

async def handle_analysis_result(message: Message, bot_msg: Message, result: dict):
    if "error" in result:
        await bot_msg.edit_text(f"❌ При анализе произошла ошибка: {result.get('analysis')}")
        return

    text = (
        f"🥗 <b>Блюда</b>: {', '.join(result.get('foods', []))}\n"
        f"🔥 <b>Калории</b>: ~{result.get('calories')} ккал\n"
        f"🥩 <b>Белки</b>: {result.get('proteins')} г\n"
        f"🧈 <b>Жиры</b>: {result.get('fats')} г\n"
        f"🥖 <b>Углеводы</b>: {result.get('carbs')} г\n\n"
        f"💡 <b>Анализ</b>: {result.get('analysis')}"
    )
    # Используем edit_text у отправленного сообщения-заглушки
    await bot_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text, ~OnboardingStates.waiting_for_weight, ~OnboardingStates.waiting_for_height, ~OnboardingStates.waiting_for_age, ~OnboardingStates.waiting_for_goal)
async def process_text_food(message: Message):
    # Пропускаем команды, которые могли упасть сюда
    if message.text.startswith('/'):
        return

    user_id = message.from_user.id
    user = await UserService.get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, пройди регистрацию с помощью команды /start")
        return

    bot_msg = await message.answer("🔄 Анализирую текст...")
    result = await analyze_food(
        input_data=message.text, 
        mime_type="text/plain", 
        language=user.get('language', 'ru')
    )
    await handle_analysis_result(message, bot_msg, result)

@router.message(F.voice)
async def process_voice_food(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = await UserService.get_user(user_id)
    if not user:
        await message.answer("Пожалуйста, пройди регистрацию с помощью команды /start")
        return

    bot_msg = await message.answer("🎧 Распознаю и анализирую голос...")
    
    # Скачиваем Voice
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    
    # Скачиваем в память
    downloaded_file = io.BytesIO()
    await bot.download_file(file.file_path, downloaded_file)
    voice_bytes = downloaded_file.getvalue()

    # Отправляем в Gemini
    result = await analyze_food(
        input_data=voice_bytes,
        mime_type="audio/ogg",
        language=user.get('language', 'ru')
    )
    
    await handle_analysis_result(message, bot_msg, result)
