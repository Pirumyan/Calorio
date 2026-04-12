import io
import os
import tempfile
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states import OnboardingStates, FeatureStates
from services.user_service import UserService
from ai.gemini import analyze_food, generate_meal_plan, generate_fridge_recipe, analyze_diary_entry, analyze_day_summary
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
        'welcome_back': "Привет! Снова рад тебя видеть.\nПросто напиши или отправь голосовое сообщение о том, что ты съел, и я все посчитаю и проанализирую!",
        'foods_label': "🥗 <b>Блюда</b>",
        'calories_label': "🔥 <b>Калории</b>",
        'proteins_label': "🥩 <b>Белки</b>",
        'fats_label': "🧈 <b>Жиры</b>",
        'carbs_label': "🥖 <b>Углеводы</b>",
        'analysis_label': "💡 <b>Анализ</b>",
        'generating_meal': "🍽 Подбираю меню...",
        'unit_cal': "ккал",
        'unit_g': "г",
        'menu_stats': "📊 Мой день",
        'menu_water': "💧 Выпил воду (250мл)",
        'menu_fridge': "🧊 Холодильник",
        'menu_diary': "📖 Дневник",
        'menu_weight': "⚖️ Вес",
        'menu_history': "⏱ История",
        'history_empty': "Ваша история пуста.",
        'history_title': "Ваши последние действия:",
        'deleted_log': "Запись удалена. Статистика обновлена.",
                'btn_delete': "❌ Удалить",
        'btn_analyze_day': "💡 Анализ дня",
        'analyzing_day': "🔄 Анализирую ваш день...",
        'water_added': "💧 Добавлено 250 мл воды! Всего за сегодня: {total} / {norm} мл",
        'fridge_prompt': "Напиши, какие продукты у тебя есть (например: курица, яйца, шпинат):",
        'fridge_generating': "👨‍🍳 Придумываю рецепт...",
        'weight_prompt': "Отправь свой текущий вес в кг (например, 70.5):",
        'weight_updated': "✅ Твой вес обновлен: {weight} кг. Я пересчитал твои суточные нормы!",
        'stats_text': "📊 <b>Твой прогресс за сегодня:</b>\n🔥 Калории: {cal} / {norm_cal} ккал\n🥩 Белки: {pro} / {norm_pro} г\n🧈 Жиры: {fat} / {norm_fat} г\n🥖 Углеводы: {car} / {norm_car} г\n💧 Вода: {water} / {norm_water} мл\n🏃 Сожжено: {burned} ккал",
        'diary_prompt': "Расскажи, как прошел твой день? (что ел, пил, занимался ли спортом, что купил):",
        'processing_diary': "📖 Анализирую твой день...",
        'diary_done': "✅ Дневник сохранен! Статистика и холодильник обновлены.",
        'btn_back': "⬅️ Назад",
        'action_cancelled': "Действие отменено. Вы вернулись в главное меню."
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
        'welcome_back': "Welcome back!\nJust write or send a voice message about what you ate, and I'll calculate and analyze everything!",
        'foods_label': "🥗 <b>Foods</b>",
        'calories_label': "🔥 <b>Calories</b>",
        'proteins_label': "🥩 <b>Proteins</b>",
        'fats_label': "🧈 <b>Fats</b>",
        'carbs_label': "🥖 <b>Carbs</b>",
        'analysis_label': "💡 <b>Analysis</b>",
        'generating_meal': "🍽 Suggesting meal plan...",
        'unit_cal': "kcal",
        'unit_g': "g",
        'menu_stats': "📊 My Day",
        'menu_water': "💧 Drank water (250ml)",
        'menu_fridge': "🧊 Fridge",
        'menu_diary': "📖 Diary",
        'menu_weight': "⚖️ Weight",
        'menu_history': "⏱ History",
        'history_empty': "Your history is empty.",
        'history_title': "Your recent actions:",
        'deleted_log': "Log deleted. Statistics updated.",
                'btn_delete': "❌ Delete",
        'btn_analyze_day': "💡 Analyze Day",
        'analyzing_day': "🔄 Analyzing your day...",
        'water_added': "💧 Added 250ml of water! Total today: {total} / {norm} ml",
        'fridge_prompt': "Write what ingredients you have (e.g., chicken, eggs, spinach):",
        'fridge_generating': "👨‍🍳 Inventing a recipe...",
        'weight_prompt': "Send your current weight in kg (e.g., 70.5):",
        'weight_updated': "✅ Your weight is updated: {weight} kg. I have recalculated your daily norms!",
        'stats_text': "📊 <b>Your progress today:</b>\n🔥 Calories: {cal} / {norm_cal} kcal\n🥩 Proteins: {pro} / {norm_pro} g\n🧈 Fats: {fat} / {norm_fat} g\n🥖 Carbs: {car} / {norm_car} g\n💧 Water: {water} / {norm_water} ml\n🏃 Burned: {burned} kcal",
        'diary_prompt': "Tell me how your day went? (what you ate, drank, did you exercise, what you bought):",
        'processing_diary': "📖 Analyzing your day...",
        'diary_done': "✅ Diary saved! Stats and fridge updated.",
        'btn_back': "⬅️ Back",
        'action_cancelled': "Action cancelled. Returned to main menu."
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
        'welcome_back': "Բարի վերադարձ!\nՈւղղակի գրեք կամ ուղարկեք ձայնային հաղորդագրություն ձեր կերածի մասին, և ես ամեն ինչ կհաշվարկեմ ու կվերլուծեմ:",
        'foods_label': "🥗 <b>Ուտեստներ</b>",
        'calories_label': "🔥 <b>Կալորիաներ</b>",
        'proteins_label': "🥩 <b>Սպիտակուցներ</b>",
        'fats_label': "🧈 <b>Ճարպեր</b>",
        'carbs_label': "🥖 <b>Ածխաջրեր</b>",
        'analysis_label': "💡 <b>Վերլուծություն</b>",
        'generating_meal': "🍽 Կազմում եմ սննդացանկ...",
        'unit_cal': "կկալ",
        'unit_g': "գ",
        'menu_stats': "📊 Իմ օրը",
        'menu_water': "💧 Խմել եմ ջուր (250մլ)",
        'menu_fridge': "🧊 Սառնարան",
        'menu_diary': "📖 Օրագիր",
        'menu_weight': "⚖️ Քաշ",
        'menu_history': "⏱ Պատմություն",
        'history_empty': "Ձեր պատմությունը դատարկ է:",
        'history_title': "Ձեր վերջին գործողությունները:",
        'deleted_log': "Գրառումը ջնջված է: Վիճակագրությունը թարմացված է:",
                'btn_delete': "❌ Ջնջել",
        'btn_analyze_day': "💡 Վերլուծել օրը",
        'analyzing_day': "🔄 Վերլուծում եм ձեր օրը...",
        'water_added': "💧 Ավելացվեց 250մլ ջուր: Այսօր ընդհանուր՝ {total} / {norm} մլ",
        'fridge_prompt': "Գրեք, թե ինչ մթերքներ ունեք (օրինակ՝ հավ, ձու, սպանախ)։",
        'fridge_generating': "👨‍🍳 Մտածում եմ բաղադրատոմս...",
        'weight_prompt': "Ուղարկեք ձեր ներկայիս քաշը կգ-ով (օրինակ՝ 70.5)։",
        'weight_updated': "✅ Ձեր քաշը թարմացվել է՝ {weight} կգ։ Ես վերահաշվարկել ենք ձեր օրական նորմաները:",
        'stats_text': "📊 <b>Ձեր առաջընթացը այսօր.</b>\n🔥 Կալորիաներ՝ {cal} / {norm_cal} կկալ\n🥩 Սպիտակուցներ՝ {pro} / {norm_pro} գ\n🧈 Ճարպեր՝ {fat} / {norm_fat} գ\n🥖 Ածխաջրեր՝ {car} / {norm_car} գ\n💧 Ջուր՝ {water} / {norm_water} մլ\n🏃 Այրված՝ {burned} կկալ",
        'diary_prompt': "Պատմեք, թե ինչպես անցավ ձեր օրը: (ինչ կերաք, խմեցիք, արդյոք սպորտով զբաղվեցիք, ինչ գնեցիք):",
        'processing_diary': "📖 Վերլուծում եմ ձեր օրը...",
        'diary_done': "✅ Օրագիրը պահպանված է: Վիճակագրությունը և սառնարանը թարմացվել են:",
        'btn_back': "⬅️ Ետ",
        'action_cancelled': "Գործողությունը չեղարկվել է: Դուք վերադարձել եք գլխավոր մենյու:"
    }
}

def get_text(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS['ru']).get(key, "")

def get_back_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(lang, 'btn_back'))]],
        resize_keyboard=True
    )
def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang, 'menu_food')), KeyboardButton(text=get_text(lang, 'menu_diary'))],
            [KeyboardButton(text=get_text(lang, 'menu_stats')), KeyboardButton(text=get_text(lang, 'menu_fridge'))],
            [KeyboardButton(text=get_text(lang, 'menu_water')), KeyboardButton(text=get_text(lang, 'menu_weight'))],
            [KeyboardButton(text=get_text(lang, 'menu_history')), KeyboardButton(text=get_text(lang, 'menu_profile'))],
            [KeyboardButton(text=get_text(lang, 'menu_lang'))]
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

def get_regenerate_keyboard(lang: str) -> InlineKeyboardMarkup:
    texts = {
        'ru': "🔄 Предложи другое меню",
        'en': "🔄 Suggest another menu",
        'am': "🔄 Առաջարկեք ուրիշ ընտրացանկ"
    }
    btn_text = texts.get(lang, texts['ru'])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=btn_text, callback_data="regen_meal")]]
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

async def handle_analysis_result(bot_msg: Message, result: dict, lang: str):
    if "error" in result:
        await bot_msg.edit_text(f"❌ {result.get('analysis')}")
        return

    # Логируем съеденное в БД
    if result.get("foods"):
        await UserService.log_user_foods(
            bot_msg.chat.id, 
            result.get("foods"),
            calories=result.get("calories", 0),
            proteins=result.get("proteins", 0),
            fats=result.get("fats", 0),
            carbs=result.get("carbs", 0)
        )

    u_cal = get_text(lang, 'unit_cal')
    u_g = get_text(lang, 'unit_g')
    
    text = (
        f"{get_text(lang, 'foods_label')}: {', '.join(result.get('foods', []))}\n"
        f"{get_text(lang, 'calories_label')}: ~{result.get('calories')} {u_cal}\n"
        f"{get_text(lang, 'proteins_label')}: {result.get('proteins')} {u_g}\n"
        f"{get_text(lang, 'fats_label')}: {result.get('fats')} {u_g}\n"
        f"{get_text(lang, 'carbs_label')}: {result.get('carbs')} {u_g}\n\n"
        f"{get_text(lang, 'analysis_label')}: {result.get('analysis')}"
    )
    await bot_msg.edit_text(text, parse_mode="HTML")

@router.message(F.text, StateFilter(None))
async def process_text_messages(message: Message, state: FSMContext):
    if message.text.startswith('/'):
        return

    user = await UserService.get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start")
        return

    lang = user.get('language', 'ru')

    # Обработка кнопок меню
    if message.text in [get_text('ru', 'menu_food'), get_text('en', 'menu_food'), get_text('am', 'menu_food')]:
        bot_msg = await message.answer(get_text(lang, 'generating_meal'))
        recent_foods = await UserService.get_user_recent_foods(message.from_user.id)
        plan = await generate_meal_plan(user, lang, recent_foods)
        await bot_msg.edit_text(plan, reply_markup=get_regenerate_keyboard(lang))
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

    # Menu Stats
    elif message.text in [get_text('ru', 'menu_stats'), get_text('en', 'menu_stats'), get_text('am', 'menu_stats')]:
        stats = await UserService.get_daily_stats(user['id'])
        norms = UserService.calculate_daily_norms(user)
        text = get_text(lang, 'stats_text').format(
            cal=stats['calories'], norm_cal=norms['calories'],
            pro=stats['proteins'], norm_pro=norms['proteins'],
            fat=stats['fats'], norm_fat=norms['fats'],
            car=stats['carbs'], norm_car=norms['carbs'],
            water=stats['water'], norm_water=norms['water'],
            burned=stats['burned']
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, 'btn_analyze_day'), callback_data="analyze_day")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    # Menu Water
    elif message.text in [get_text('ru', 'menu_water'), get_text('en', 'menu_water'), get_text('am', 'menu_water')]:
        await UserService.add_water(user['id'], 250)
        stats = await UserService.get_daily_stats(user['id'])
        norms = UserService.calculate_daily_norms(user)
        text = get_text(lang, 'water_added').format(total=stats['water'], norm=norms['water'])
        await message.answer(text)
        return

    # Menu Fridge
    elif message.text in [get_text('ru', 'menu_fridge'), get_text('en', 'menu_fridge'), get_text('am', 'menu_fridge')]:
        fridge_items = await UserService.get_fridge_items(user['id'])
        if fridge_items:
            items_str = ", ".join([f"{i['item_name']} ({i['quantity']})" if i['quantity'] else i['item_name'] for i in fridge_items])
            await message.answer(f"🧊 <b>В твоем холодильнике:</b>\n{items_str}\n\n{get_text(lang, 'fridge_prompt')}", parse_mode="HTML", reply_markup=get_back_keyboard(lang))
        else:
            await message.answer(get_text(lang, 'fridge_prompt'), reply_markup=get_back_keyboard(lang))
        await state.set_state(FeatureStates.waiting_for_fridge_ingredients)
        return

    # Menu Diary
    elif message.text in [get_text('ru', 'menu_diary'), get_text('en', 'menu_diary'), get_text('am', 'menu_diary')]:
        await message.answer(get_text(lang, 'diary_prompt'), reply_markup=get_back_keyboard(lang))
        await state.set_state(FeatureStates.waiting_for_diary)
        return

    # Menu History
    elif message.text in [get_text('ru', 'menu_history'), get_text('en', 'menu_history'), get_text('am', 'menu_history')]:
        history = await UserService.get_recent_history(user['id'])
        if not history:
            await message.answer(get_text(lang, 'history_empty'))
            return
            
        await message.answer(get_text(lang, 'history_title'))
        for item in history:
            item_type = "🍽" if item['type'] == 'food' else "💧"
            desc = item['description']
            if item['type'] == 'food':
                desc = desc.strip('{}').replace('"', '').replace(',', ', ')
            else:
                desc = f"{desc} ml"
            time_str = item['created_at'].strftime("%H:%M")
            
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=get_text(lang, 'btn_delete'), callback_data=f"del_{item['type']}_{item['id']}")]]
            )
            await message.answer(f"{item_type} [{time_str}] {desc}", reply_markup=kb)
        return

    # Menu Weight
    elif message.text in [get_text('ru', 'menu_weight'), get_text('en', 'menu_weight'), get_text('am', 'menu_weight')]:
        await message.answer(get_text(lang, 'weight_prompt'), reply_markup=get_back_keyboard(lang))
        await state.set_state(FeatureStates.waiting_for_new_weight)
        return

    # Если это не кнопка меню, значит это текст про еду
    bot_msg = await message.answer(get_text(lang, 'analyzing_text'))
    result = await analyze_food(
        input_data=message.text, 
        mime_type="text/plain", 
        language=lang
    )
    await handle_analysis_result(bot_msg, result, lang)
    try:
        await message.delete()
    except:
        pass

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
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
        temp_path = temp_audio.name
        
    await bot.download_file(file.file_path, destination=temp_path)

    result = await analyze_food(
        input_data=temp_path,
        mime_type="audio/ogg",
        language=lang
    )
    
    try:
        os.remove(temp_path)
    except OSError:
        pass
    
    await handle_analysis_result(bot_msg, result, lang)
    try:
        await message.delete()
    except:
        pass

@router.callback_query(F.data == "analyze_day")
async def process_analyze_day(callback: CallbackQuery):
    user = await UserService.get_user(callback.from_user.id)
    lang = user.get('language', 'ru')
    
    # Сначала отвечаем на колбэк, чтобы кнопка не "висела"
    await callback.answer(get_text(lang, 'analyzing_day'))
    
    # Собираем данные
    stats = await UserService.get_daily_stats(user['id'])
    norms = UserService.calculate_daily_norms(user)
    today_foods = await UserService.get_today_foods(user['id'])
    
    # Запрос к ИИ
    advice = await analyze_day_summary(stats, norms, today_foods, user, lang)
    
    # Отправляем результат
    await callback.message.answer(f"<b>{get_text(lang, 'btn_analyze_day')}:</b>\n\n{advice}", parse_mode="HTML")

@router.callback_query(F.data.startswith("del_"))
async def process_delete_log(callback: CallbackQuery):
    user = await UserService.get_user(callback.from_user.id)
    lang = user.get('language', 'ru') if user else 'ru'
    
    parts = callback.data.split('_')
    if len(parts) == 3:
        log_type = parts[1]
        log_id = int(parts[2])
        await UserService.delete_log(log_type, log_id)
        
        try:
            await callback.message.edit_text(f"<s>{callback.message.text}</s>\n\n✅ {get_text(lang, 'deleted_log')}", parse_mode="HTML")
        except:
            await callback.message.delete()
            await callback.message.answer(f"✅ {get_text(lang, 'deleted_log')}")
            
    await callback.answer()

@router.callback_query(F.data == "regen_meal")
async def process_regenerate_meal(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await UserService.get_user(user_id)
    if not user:
        return
    lang = user.get('language', 'ru')
    
    await callback.message.edit_text(get_text(lang, 'generating_meal'))
    recent_foods = await UserService.get_user_recent_foods(user_id)
    
    plan = await generate_meal_plan(user, lang, recent_foods, is_regenerate=True)
    await callback.message.edit_text(plan, reply_markup=get_regenerate_keyboard(lang))
    await callback.answer()

@router.message(F.text.in_([TEXTS['ru']['btn_back'], TEXTS['en']['btn_back'], TEXTS['am']['btn_back']]))
async def process_cancel(message: Message, state: FSMContext):
    user = await UserService.get_user(message.from_user.id)
    lang = user.get('language', 'ru') if user else 'ru'
    
    await state.clear()
    await message.answer(get_text(lang, 'action_cancelled'), reply_markup=get_main_keyboard(lang))

@router.message(FeatureStates.waiting_for_new_weight, F.text)
async def process_new_weight(message: Message, state: FSMContext):
    user = await UserService.get_user(message.from_user.id)
    lang = user.get('language', 'ru') if user else 'ru'
    try:
        weight = float(message.text.replace(',', '.'))
        await UserService.update_weight_and_log(message.from_user.id, weight)
        await message.answer(get_text(lang, 'weight_updated').format(weight=weight), reply_markup=get_main_keyboard(lang))
        await state.clear()
    except ValueError:
        await message.answer(get_text(lang, 'error_number'))

@router.message(FeatureStates.waiting_for_fridge_ingredients, F.text)
async def process_fridge_ingredients(message: Message, state: FSMContext):
    user = await UserService.get_user(message.from_user.id)
    lang = user.get('language', 'ru') if user else 'ru'
    
    bot_msg = await message.answer(get_text(lang, 'fridge_generating'))
    norms = UserService.calculate_daily_norms(user)
    
    recipe = await generate_fridge_recipe(message.text, user, norms, lang)
    await bot_msg.edit_text(recipe)
    await message.answer("✅", reply_markup=get_main_keyboard(lang))
    await state.clear()

@router.message(FeatureStates.waiting_for_diary, F.text | F.voice)
async def process_diary_entry_handler(message: Message, state: FSMContext, bot: Bot):
    user = await UserService.get_user(message.from_user.id)
    lang = user.get('language', 'ru')
    bot_msg = await message.answer(get_text(lang, 'processing_diary'))
    
    input_data = ""
    mime_type = "text/plain"
    
    if message.voice:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_path = temp_audio.name
        await bot.download_file(file.file_path, destination=temp_path)
        input_data = temp_path
        mime_type = "audio/ogg"
    else:
        input_data = message.text

    result = await analyze_diary_entry(input_data, mime_type, lang)
    
    if mime_type == "audio/ogg":
        try:
            os.remove(input_data)
        except OSError:
            pass
    
    if "error" in result:
        await bot_msg.edit_text(f"❌ {result.get('error')}")
        return

    # Process Food
    foods = result.get("foods", [])
    if foods:
        food_names = [f["name"] for f in foods]
        total_cal = sum(f.get("calories", 0) for f in foods)
        total_pro = sum(f.get("proteins", 0) for f in foods)
        total_fat = sum(f.get("fats", 0) for f in foods)
        total_car = sum(f.get("carbs", 0) for f in foods)
        await UserService.log_user_foods(user['id'], food_names, total_cal, total_pro, total_fat, total_car)

    # Process Water
    water = result.get("water", 0)
    if water > 0:
        await UserService.add_water(user['id'], water)

    # Process Exercise
    exercises = result.get("exercises", [])
    for ex in exercises:
        await UserService.log_exercise(user['id'], ex.get("name"), ex.get("calories_burned", 0))

    # Process Fridge
    for item in result.get("fridge_add", []):
        await UserService.add_fridge_item(user['id'], item)
    for item in result.get("fridge_remove", []):
        await UserService.remove_fridge_item(user['id'], item)

    analysis_text = result.get("analysis", "")
    await bot_msg.edit_text(f"{analysis_text}\n\n{get_text(lang, 'diary_done')}")
    await message.answer("✅", reply_markup=get_main_keyboard(lang))
    await state.clear()
