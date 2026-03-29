import io
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states import OnboardingStates
from services.user_service import UserService
from ai.gemini import analyze_food
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

TEXTS = {
    'ru': {
        'weight': "Давай познакомимся. Введи свой <b>вес в кг</b> (например, 70):",
        'height': "Отлично. Теперь введи свой <b>рост в см</b> (например, 175):",
        'age': "Теперь укажи свой <b>возраст</b> (полных лет):",
        'goal': "Какая у тебя <b>цель</b>?\n(например: похудеть, набрать массу, поддержать форму)",
        'done': "💪 Профиль сохранен! Теперь ты можешь отправлять мне текст или голосовые сообщения с описанием своей еды, а я оценю калории и БЖУ.",
        'analyzing_text': "🔄 Анализирую текст...",
        'analyzing_voice': "🎧 Распознаю и анализирую голос...",
        'error_number': "Пожалуйста, введи число.",
        'menu_food': "🍽 Мое питание",
        'menu_profile': "👤 Профиль",
        'menu_lang': "⚙️ Язык",
        'profile_text': "<b>Твой профиль:</b>\n⚖️ Вес: {weight} кг\n📏 Рост: {height} см\n🎂 Возраст: {age} лет\n🎯 Цель: {goal}",
        'welcome_back': "Привет! Снова рад тебя видеть.\nПросто напиши или отправь голосовое сообщение о том, что ты съел, и я все посчитаю и проанализирую!"
    },
    'en': {
        'weight': "Let's get acquainted. Enter your <b>weight in kg</b> (e.g. 70):",
        'height': "Great. Now enter your <b>height in cm</b> (e.g. 175):",
        'age': "Now specify your <b>age</b> (full years):",
        'goal': "What is your <b>goal</b>?\n(e.g. lose weight, gain mass, keep fit)",
        'done': "💪 Profile saved! You can now send me text or voice messages with your food descriptions.",
        'analyzing_text': "🔄 Analyzing text...",
        'analyzing_voice': "🎧 Recognizing and analyzing voice...",
        'error_number': "Please enter a valid number.",
        'menu_food': "🍽 My food",
        'menu_profile': "👤 Profile",
        'menu_lang': "⚙️ Language",
        'profile_text': "<b>Your Profile:</b>\n⚖️ Weight: {weight} kg\n📏 Height: {height} cm\n🎂 Age: {age} years\n🎯 Goal: {goal}",
        'welcome_back': "Welcome back!\nJust write or send a voice message about what you ate, and I'll calculate and analyze everything!"
    },
    'am': {
        'weight': "Եկեք ծանոթանանք: Մուտքագրեք ձեր <b>քաշը կգ-ով</b> (օրինակ՝ 70)։",
        'height': "Գերազանց: Այժմ մուտքագրեք ձեր <b>հասակը սմ-ով</b> (օրինակ՝ 175)։",
        'age': "Այժմ նշեք ձեր <b>տարիքը</b> (ամբողջ տարիներով)։",
        'goal': "Ո՞րն է ձեր <b>նպատակը</b>։\n(օրինակ՝ նիհարել, մկանային զանգված հավաքել, պահպանել կազմվածքը)",
        'done': "💪 Պրոֆիլը պահպանված է! Այժմ կարող եք ուղարկել տեքստային կամ ձայնային հաղորդագրություններ ձեր սննդի մասին։",
        'analyzing_text': "🔄 Վերլուծում եմ տեքստը...",
        'analyzing_voice': "🎧 Ճանաչում և վերլուծում եմ ձայնը...",
        'error_number': "Խնդրում ենք մուտքագրել թիվ:",
        'menu_food': "🍽 Իմ սնունդը",
        'menu_profile': "👤 Պրոֆիլ",
        'menu_lang': "⚙️ Լեզու",
        'profile_text': "<b>Ձեր պրոֆիլը.</b>\n⚖️ Քաշը՝ {weight} կգ\n📏 Հասակը՝ {height} սմ\n🎂 Տարիքը՝ {age} տարի\n🎯 Նպատակը՝ {goal}",
        'welcome_back': "Բարի վերադարձ!\nՈւղղակի գրեք կամ ուղարկեք ձայնային հաղորդագրություն ձեր կերածի մասին, և ես ամեն ինչ կհաշվարկեմ ու կվերլուծեմ:"
    }
}

def get_text(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS['ru']).get(key, "")

def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, 'menu_food'))],
            [KeyboardButton(text=get_text(lang, 'menu_profile')), KeyboardButton(text=get_text(lang, 'menu_lang'))]
        ],
        resize_keyboard=True
    )
    return kb

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="🇦🇲 Հայերեն", callback_data="lang_am")]
        ]
    )

# --- АДМИН ПАНЕЛЬ ---

@router.message(Command("users"), StateFilter(None))
async def admin_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await UserService.get_users_count()
    await message.answer(f"📊 Всего пользователей в базе: <b>{count}</b>", parse_mode="HTML")

# --- ОНБОРДИНГ ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await UserService.get_user(message.from_user.id)
    if user:
        lang = user.get('language', 'ru')
        await message.answer(
            get_text(lang, 'welcome_back'),
            reply_markup=get_main_keyboard(lang)
        )
    else:
        await message.answer(
            "Please choose your language / Выберите язык / Ընտրեք լեզուն:",
            reply_markup=get_language_keyboard()
        )
        await state.set_state(OnboardingStates.waiting_for_language)

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split('_')[1]
    
    current_state = await state.get_state()
    
    # Если юзер в процессе регистрации
    if current_state == OnboardingStates.waiting_for_language.state:
        await state.update_data(language=lang_code)
        await callback.message.edit_text(get_text(lang_code, 'weight'), parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_weight)
    else:
        # Если это изменение языка через меню
        user_id = callback.from_user.id
        user = await UserService.get_user(user_id)
        if user:
            await UserService.update_language(user_id, lang_code)
            await callback.message.delete()
            await callback.message.answer(
                get_text(lang_code, 'welcome_back'),
                reply_markup=get_main_keyboard(lang_code)
            )
            
    await callback.answer()

@router.message(OnboardingStates.waiting_for_weight, F.text)
async def process_weight(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')
    try:
        weight = float(message.text.replace(',', '.'))
        await state.update_data(weight=weight)
        await message.answer(get_text(lang, 'height'), parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_height)
    except ValueError:
        await message.answer(get_text(lang, 'error_number'))

@router.message(OnboardingStates.waiting_for_height, F.text)
async def process_height(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')
    try:
        height = float(message.text.replace(',', '.'))
        await state.update_data(height=height)
        await message.answer(get_text(lang, 'age'), parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_age)
    except ValueError:
        await message.answer(get_text(lang, 'error_number'))

@router.message(OnboardingStates.waiting_for_age, F.text)
async def process_age(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('language', 'ru')
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.answer(get_text(lang, 'goal'), parse_mode="HTML")
        await state.set_state(OnboardingStates.waiting_for_goal)
    except ValueError:
        await message.answer(get_text(lang, 'error_number'))

@router.message(OnboardingStates.waiting_for_goal, F.text)
async def process_goal(message: Message, state: FSMContext):
    goal = message.text
    data = await state.get_data()
    lang = data.get('language', 'ru')
    
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
        get_text(lang, 'done'),
        reply_markup=get_main_keyboard(lang),
        parse_mode="HTML"
    )

# --- МЕНЮ И АНАЛИЗ ЕДЫ ---

async def handle_analysis_result(bot_msg: Message, result: dict):
    if "error" in result:
        await bot_msg.edit_text(f"❌ {result.get('analysis')}")
        return

    text = (
        f"🥗 <b>Блюда</b>: {', '.join(result.get('foods', []))}\n"
        f"🔥 <b>Калории</b>: ~{result.get('calories')} ккал\n"
        f"🥩 <b>Белки</b>: {result.get('proteins')} г\n"
        f"🧈 <b>Жиры</b>: {result.get('fats')} г\n"
        f"🥖 <b>Углеводы</b>: {result.get('carbs')} г\n\n"
        f"💡 <b>Анализ</b>: {result.get('analysis')}"
    )
    await bot_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text, StateFilter(None))
async def process_text_messages(message: Message):
    if message.text.startswith('/'):
        return

    user = await UserService.get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start")
        return

    lang = user.get('language', 'ru')

    # Обработка кнопок меню
    if message.text in [get_text('ru', 'menu_food'), get_text('en', 'menu_food'), get_text('am', 'menu_food')]:
        await message.answer(get_text(lang, 'welcome_back'), reply_markup=get_main_keyboard(lang))
        return

    elif message.text in [get_text('ru', 'menu_profile'), get_text('en', 'menu_profile'), get_text('am', 'menu_profile')]:
        profile_msg = get_text(lang, 'profile_text').format(
            weight=user.get('weight'),
            height=user.get('height'),
            age=user.get('age'),
            goal=user.get('goal')
        )
        await message.answer(profile_msg, parse_mode="HTML", reply_markup=get_main_keyboard(lang))
        return

    elif message.text in [get_text('ru', 'menu_lang'), get_text('en', 'menu_lang'), get_text('am', 'menu_lang')]:
        await message.answer("Please choose your language / Выберите язык / Ընտրեք լեզուն:", reply_markup=get_language_keyboard())
        return

    # Если это не кнопка меню, значит это текст про еду
    bot_msg = await message.answer(get_text(lang, 'analyzing_text'))
    result = await analyze_food(
        input_data=message.text, 
        mime_type="text/plain", 
        language=lang
    )
    await handle_analysis_result(bot_msg, result)

@router.message(F.voice, StateFilter(None))
async def process_voice_food(message: Message, bot: Bot):
    user = await UserService.get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start")
        return

    lang = user.get('language', 'ru')
    bot_msg = await message.answer(get_text(lang, 'analyzing_voice'))
    
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    
    downloaded_file = io.BytesIO()
    await bot.download_file(file.file_path, downloaded_file)
    voice_bytes = downloaded_file.getvalue()

    result = await analyze_food(
        input_data=voice_bytes,
        mime_type="audio/ogg",
        language=lang
    )
    
    await handle_analysis_result(bot_msg, result)
