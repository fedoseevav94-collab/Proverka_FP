from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from damage_bot.config import Settings
from damage_bot.db import init_db, make_engine, make_session_factory
from damage_bot.handlers import register_handlers
from damage_bot.reminders import reminder_loop


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = Settings()
    engine = make_engine(settings.database_url)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    register_handlers(dp, session_factory, settings)

    reminder_task = asyncio.create_task(reminder_loop(bot, session_factory, settings))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminder_task.cancel()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

