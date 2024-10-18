import logging
import asyncio
import sys
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from handlers import router
from main import dp, SchedulerMiddleware, scheduler


async def main() -> None:
    dp.include_router(router)
    dp.update.middleware(SchedulerMiddleware(scheduler=scheduler))

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
