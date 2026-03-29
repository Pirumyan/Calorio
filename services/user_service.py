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
    async def log_user_foods(user_id: int, foods: list[str]):
        if not foods:
            return
        query = "INSERT INTO food_logs (user_id, foods) VALUES ($1, $2)"
        async with db.pool.acquire() as connection:
            await connection.execute(query, user_id, foods)

    @staticmethod
    async def get_user_recent_foods(user_id: int, limit: int = 10) -> list[str]:
        query = "SELECT foods FROM food_logs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2"
        async with db.pool.acquire() as connection:
            records = await connection.fetch(query, user_id, limit)
            all_foods = []
            for r in records:
                all_foods.extend(r['foods'])
            # Return unique items via set while preserving some order or just returning set
            return list(set(all_foods))
