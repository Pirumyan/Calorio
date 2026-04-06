from aiogram.fsm.state import State, StatesGroup

class OnboardingStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_goal = State()

class FeatureStates(StatesGroup):
    waiting_for_new_weight = State()
    waiting_for_fridge_ingredients = State()
    waiting_for_diary = State()
