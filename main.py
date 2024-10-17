import logging
import asyncio
import sys

from aiogram import Bot, Dispatcher, types, BaseMiddleware, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler


from config import TOKEN
from handlers import router, scheduler


bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()  # запускает программу, к нему цепляются роутеры


@dp.message(CommandStart())
async def command_start_handler(message: types.Message, bot: Bot):
    await bot.send_message(message.chat.id, f"🪴 Привет! Я помогу тебе не забыть полить свои любимые растения 🪴. \n\n"
                                            f"Чтобы добавить растение 🌸 в календарь полива, введите /flowers")


@dp.message(Command("help"))
async def handle_help(message: types.Message):
    text = ("Список доступных команд:\n"
            "/start - начало работы с ботом\n"
            "/flowers - управление напоминаниями")
    await message.answer(text=text)


async def main() -> None:
    scheduler.start()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__=="__main__":
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout
    )
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()