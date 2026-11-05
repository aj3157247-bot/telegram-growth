import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from config import settings
from database import Database
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("growth_manager")

async def main():
    if not settings.bot_token or settings.bot_token == "PASTE_BOTFATHER_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN را در فایل .env تنظیم کن.")
    if settings.owner_id <= 0:
        raise RuntimeError("OWNER_ID باید شناسه عددی تلگرام مالک باشد.")

    db = Database(settings.db_path)
    await db.initialize()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["db"] = db
    dp["settings"] = settings
    dp.include_router(router)

    me = await bot.get_me()
    log.info("Bot started: @%s (id=%s)", me.username, me.id)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
