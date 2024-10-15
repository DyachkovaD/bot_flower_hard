import logging
import asyncio
import sys
import logging
import asyncio
import sys

from aiogram import Bot, Dispatcher, types, BaseMiddleware, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from token_data import TOKEN
from handlers import router, Actions
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from datetime import datetime, timedelta

scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
scheduler.start()
dp = Dispatcher()  # запускает программу, к нему цепляются роутеры


# Позволяет доставать scheduler из агрументов функции
class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler: AsyncIOScheduler):
        super().__init__()
        self._scheduler = scheduler

    async def __call__(self, handler, event, data):
        # прокидываем в словарь состояния scheduler
        data['scheduler'] = self._scheduler
        return await handler(event, data)



flowers = {}


@dp.message(CommandStart())
async def command_start_handler(message: types.Message, bot: Bot):
    await bot.send_message(message.chat.id, f"🪴 Привет! Я помогу тебе не забыть полить свои любимые растения 🪴. \n\n"
                                            f"Чтобы добавить растение 🌸 в календарь полива, введите\n"
                                            f"/add (цветок) (сколько раз в неделю нужно поливать) \n\n"
                                            f"Например: Фиалка 3")


async def main() -> None:
    dp.include_router(router)
    dp.update.middleware(SchedulerMiddleware(scheduler=scheduler))

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    await dp.start_polling(bot)

if __name__=="__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout
    )
    asyncio.run(main())