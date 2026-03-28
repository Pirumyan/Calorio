import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from bot.handlers import router
from database.db import db

# Настраиваем минимальное логирование, чтобы не грузить CPU/RAM
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    # Запускаем фоновую задачу для Long Polling
    app['polling_task'] = asyncio.create_task(dp.start_polling(bot))

async def on_cleanup(app):
    logger.info("Shutting down...")
    app['polling_task'].cancel()
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
