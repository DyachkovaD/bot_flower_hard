from aiogram import Router, types
from aiogram.filters import Command, CommandObject
import psycopg2
from contextlib import closing
from aiogram import BaseMiddleware, F, Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

router = Router()


@router.message(Command("add"))
async def add_flower(message: types.Message, bot: Bot, command: CommandObject):
    # Проверяем правильно ли пользователь ввёл команду
    try:
        args = command.args.split()
        int(args[-1])
    # Если пользователь не ввёл аргументы
    except AttributeError:
        await message.answer(
            "Ошибка: не переданы аргументы"
        )
        return
    # Если пользователь не ввёл (ввёл неправильно) частоту полива
    except ValueError:
        await message.answer(
            "Ошибка: неправильно переданы аргументы\n"
            "Пример: Алоэ 3"
        )
        return

    flower, frequency = command.args.split()[:-1], command.args.split()[-1]
    flower = ' '.join(flower)   # если название растения из нескольких слов
    flowers[flower] = frequency

    #    шедулер переделать
    # scheduler.add_job(bot.send_message, 'interval', days=int(frequency),
    #                   args=[message.from_user.id, f"Напоминаю полить 🌧️ {flower}"])
    #
    # watering = datetime.now() + timedelta(seconds=int(frequency))
    # await message.answer(f"Следующий полив 💧: {datetime.strftime(watering, '%A %H:%M')}")