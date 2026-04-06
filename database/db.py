import asyncpg
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(DATABASE_URL)
            await self.init_db()
            logger.info("Connected to PostgreSQL (Supabase) successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise e

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def init_db(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            weight REAL,
            height REAL,
            age INTEGER,
            goal TEXT,
            language VARCHAR(2) DEFAULT 'ru',
            subscription_type VARCHAR(10) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS food_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            foods TEXT[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE food_logs ADD COLUMN IF NOT EXISTS calories REAL DEFAULT 0;
        ALTER TABLE food_logs ADD COLUMN IF NOT EXISTS proteins REAL DEFAULT 0;
        ALTER TABLE food_logs ADD COLUMN IF NOT EXISTS fats REAL DEFAULT 0;
        ALTER TABLE food_logs ADD COLUMN IF NOT EXISTS carbs REAL DEFAULT 0;

        CREATE TABLE IF NOT EXISTS water_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS weight_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            weight REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS fridge_items (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            item_name TEXT NOT NULL,
            quantity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS exercise_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            description TEXT,
            calories_burned REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        async with self.pool.acquire() as connection:
            await connection.execute(query)

# Единый инстанс для использования во всем приложении
db = Database()
