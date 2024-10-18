from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
scheduler.start()
dp = Dispatcher()  # запускает программу, к нему цепляются роутеры


# Позволяет доставать scheduler из агрументов функции
class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler: AsyncIOScheduler):
        super().__init__()
        self._scheduler = scheduler

    async def __call__(self, handler, event, data):
        # прокидываем в словарь состояния scheduler
        data["scheduler"] = self._scheduler
        return await handler(event, data)


flowers = {}


@dp.message(CommandStart())
async def command_start_handler(message: types.Message, bot: Bot):
    await bot.send_message(
        message.chat.id,
        "🪴 Привет! Я помогу тебе не забыть полить свои любимые растения 🪴. \n\n"
        "Чтобы добавить растение 🌸 в календарь полива, введите\n"
        "/add (цветок) (сколько раз в неделю нужно поливать) \n\n"
        "Например: Фиалка 3",
    )


# async def main() -> None:
#     dp.include_router(router)
#     dp.update.middleware(SchedulerMiddleware(scheduler=scheduler))
#
#     bot = Bot(
#         token=TOKEN,
#         default=DefaultBotProperties(parse_mode=ParseMode.HTML)
#     )
#     await dp.start_polling(bot)

# if __name__=="__main__":
#     logging.basicConfig(
#         level=logging.INFO,
#         stream=sys.stdout
#     )
#     asyncio.run(main())
