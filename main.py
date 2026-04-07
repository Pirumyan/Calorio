import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from bot.handlers import router
from database.db import db

# Настраиваем минимальное логирование, чтобы не грузить CPU/RAM
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from zoneinfo import ZoneInfo

async def water_reminder_task(bot: Bot):
    while True:
        await asyncio.sleep(4 * 3600)  # Every 4 hours
        now = datetime.now(ZoneInfo('Asia/Yerevan'))
        if not (10 <= now.hour < 23):
            continue
            
        try:
            query = """
            SELECT id, language FROM users 
            WHERE id NOT IN (
                SELECT user_id FROM water_logs WHERE DATE(created_at) = CURRENT_DATE
            )
            """
            async with db.pool.acquire() as connection:
                users = await connection.fetch(query)
                for user in users:
                    lang = user['language'] or 'ru'
                    texts = {
                        'ru': "💧 Напоминание: ты еще не пил(а) воду сегодня! Не забывай поддерживать водный баланс.",
                        'en': "💧 Reminder: you haven't drank water today! Keep hydrated.",
                        'am': "💧 Հիշեցում. դուք այսօր ջուր չեք խմել: Մի մոռացեք ջուր խմել:"
                    }
                    rem_text = texts.get(lang, texts['ru'])
                    try:
                        await bot.send_message(user['id'], rem_text)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Water reminder error: {e}")

async def handle(request):
    """Простой HTTP-ответ для проверки состояния сервера Render"""
    return web.Response(text="Bot is running!")

async def on_startup(app):
    logger.info("Starting bot and connecting to DB...")
    await db.connect()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    app['bot'] = bot
    app['dp'] = dp
    
    # Удаляем вебхуки (работаем через long-polling)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем фоновые задачи
    app['polling_task'] = asyncio.create_task(dp.start_polling(bot))
    app['water_task'] = asyncio.create_task(water_reminder_task(bot))

async def on_cleanup(app):
    logger.info("Shutting down...")
    app['polling_task'].cancel()
    if 'water_task' in app:
        app['water_task'].cancel()
    await app['bot'].session.close()
    await db.close()

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/', handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    
    # Render передает номер порта в переменную окружения PORT (по умолчанию 8080)
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting web server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)
