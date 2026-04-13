import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

if not GOOGLE_API_KEY and not GROQ_API_KEY:
    raise ValueError("Neither GOOGLE_API_KEY nor GROQ_API_KEY is set. At least one AI provider is required.")

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
