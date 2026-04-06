from database.db import db
from aiogram.types import Message

class UserService:
    @staticmethod
    async def get_user(user_id: int):
        query = "SELECT * FROM users WHERE id = $1"
        async with db.pool.acquire() as connection:
            record = await connection.fetchrow(query, user_id)
            return dict(record) if record else None

    @staticmethod
    async def create_user(user_id: int, weight: float, height: float, age: int, goal: str, language: str = 'ru'):
        query = """
        INSERT INTO users (id, weight, height, age, goal, language)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO UPDATE 
        SET weight = EXCLUDED.weight,
            height = EXCLUDED.height,
            age = EXCLUDED.age,
            goal = EXCLUDED.goal,
            language = EXCLUDED.language;
        """
        async with db.pool.acquire() as connection:
            await connection.execute(query, user_id, weight, height, age, goal, language)

    @staticmethod
    async def get_users_count() -> int:
        query = "SELECT COUNT(*) FROM users"
        async with db.pool.acquire() as connection:
            return await connection.fetchval(query)

    @staticmethod
    async def update_language(user_id: int, language: str):
        query = "UPDATE users SET language = $1 WHERE id = $2"
        async with db.pool.acquire() as connection:
            await connection.execute(query, language, user_id)

    @staticmethod
    def get_user_language(message: Message) -> str:
        # Для начала просто возвращаем язык клиента из ТГ, если не сохранен
        lang = message.from_user.language_code
        if lang and lang.startswith('en'):
            return 'en'
        elif lang and lang.startswith('hy') or lang and lang.startswith('am'):
            return 'am'
        return 'ru'

    @staticmethod
    async def log_user_foods(user_id: int, foods: list[str], calories: float = 0, proteins: float = 0, fats: float = 0, carbs: float = 0):
        if not foods:
            return
        query = """
        INSERT INTO food_logs (user_id, foods, calories, proteins, fats, carbs) 
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        async with db.pool.acquire() as connection:
            await connection.execute(query, user_id, foods, calories or 0, proteins or 0, fats or 0, carbs or 0)

    @staticmethod
    async def add_water(user_id: int, amount: int):
        query = "INSERT INTO water_logs (user_id, amount) VALUES ($1, $2)"
        async with db.pool.acquire() as connection:
            await connection.execute(query, user_id, amount)

    @staticmethod
    async def get_daily_stats(user_id: int) -> dict:
        food_query = """
        SELECT COALESCE(SUM(calories), 0) as calories, 
               COALESCE(SUM(proteins), 0) as proteins, 
               COALESCE(SUM(fats), 0) as fats, 
               COALESCE(SUM(carbs), 0) as carbs
        FROM food_logs 
        WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE
        """
        water_query = """
        SELECT COALESCE(SUM(amount), 0) as water_amount 
        FROM water_logs 
        WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE
        """
        async with db.pool.acquire() as connection:
            food_stats = await connection.fetchrow(food_query, user_id)
            water_stats = await connection.fetchval(water_query, user_id)
        
        return {
            'calories': food_stats['calories'],
            'proteins': food_stats['proteins'],
            'fats': food_stats['fats'],
            'carbs': food_stats['carbs'],
            'water': water_stats
        }

    @staticmethod
    async def update_weight_and_log(user_id: int, weight: float):
        update_query = "UPDATE users SET weight = $1 WHERE id = $2"
        log_query = "INSERT INTO weight_logs (user_id, weight) VALUES ($1, $2)"
        async with db.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(update_query, weight, user_id)
                await connection.execute(log_query, user_id, weight)

    @staticmethod
    def calculate_daily_norms(user: dict) -> dict:
        weight = user.get('weight', 70)
        height = user.get('height', 170)
        age = user.get('age', 30)
        goal = user.get('goal', '').lower()
        
        # Mifflin-St Jeor (average for men/women)
        bmr = 10 * weight + 6.25 * height - 5 * age - 78
        tdee = bmr * 1.3  # Activity multiplier (light activity)
        
        loss_keywords = ['похуд', 'сброс', 'lose', 'weight loss', 'նիհար']
        gain_keywords = ['набра', 'масс', 'gain', 'build', 'ձեռք', 'քաշ']
        
        target_calories = tdee
        if any(k in goal for k in loss_keywords):
            target_calories *= 0.8
        elif any(k in goal for k in gain_keywords):
            target_calories *= 1.2
            
        proteins = target_calories * 0.3 / 4
        fats = target_calories * 0.3 / 9
        carbs = target_calories * 0.4 / 4
        
        water_norm = weight * 30 # 30ml per kg
        
        return {
            'calories': round(target_calories),
            'proteins': round(proteins),
            'fats': round(fats),
            'carbs': round(carbs),
            'water': round(water_norm)
        }

    @staticmethod
    async def get_user_recent_foods(user_id: int, limit: int = 10) -> list[str]:
        query = "SELECT foods FROM food_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2"
        async with db.pool.acquire() as connection:
            records = await connection.fetch(query, user_id, limit)
            all_foods = []
            for r in records:
                all_foods.extend(r['foods'])
            return list(set(all_foods))
