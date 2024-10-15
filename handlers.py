import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from contextlib import closing
from aiogram import BaseMiddleware, F, Bot
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery
from aiogram.utils import markdown
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from keyboards import build_flowers_kb, NotificationCallback, build_weekdays_kb, days_of_week

router = Router()

flowers = {}
list_of_days = []


class Notification(StatesGroup):
    flower_name = State()
    weekdays = State()


class EditNotificationCallback(CallbackData, prefix="edit"):
    flower_name: str
    action: str


# Обработка команды /cancel во время опроса
@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Отмена состояния %r", current_state)
    await state.clear()
    await message.answer(
        "Отменено."
    )


# Обработка команды /flowers для управления напоминаниями
@router.message(Command("flowers"))
async def handle_flowers(message: types.Message):
    text = "Управление напоминаниями:"
    await message.answer(text=text, reply_markup=build_flowers_kb())



# Запуск опроса, запрос наименования растения от пользователя
@router.callback_query(NotificationCallback.filter(F.action == "add"))
async def handle_add_notification(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(Notification.flower_name)
    await call.message.edit_text(
        text="Напишите название растения.\n"
             "Для отмены введите /cancel",
    )


# Продолжение опроса, выбор дней недели для напоминаний
@router.message(Notification.flower_name)
async def handle_add_notification_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Некорректный ввод. Пожалуйста, введите наименование растения",)
        return
    await state.update_data(flower_name=message.text)
    await state.set_state(Notification.weekdays)
    await message.answer(
        f"Вы добавляете напоминание для полива растения: {markdown.hbold(message.text)}.\n"
        "Выберите дни недели для полива. Определившись с выбором, нажмите 'Готово!'\n"
        "Для отмены введите /cancel",
        reply_markup=build_weekdays_kb()
    )


# Вывод результатов опроса
async def send_results(call: CallbackQuery, data: dict, days: str):
    text = markdown.text(
        "Уведомление добавлено:"
        "",
        markdown.text("Наименование растения: ", markdown.hbold(data["flower_name"])),
        markdown.text(f"Выбранные дни полива: {markdown.hbold(days)}"),
        sep='\n',
    )
    await call.message.edit_text(text=text)


# Обработка выбранных дней недели. На текущий момент реализация весьма топорна, call'ы складываются в list_of_days
# пока пользователь не жмякнет Ready. Нет возможности отменить неправильный выбор - только пересоздавать напоминание.
@router.callback_query(Notification.weekdays, lambda call: True)
async def handle_days_of_week(call: CallbackQuery, state: FSMContext):
    global list_of_days
    global flowers
    if call.data == "week:ready":
        days = ", ".join(list_of_days)
        weekdays = [days_of_week[x][1] for x in list_of_days]
        list_of_days = []
        data = await state.update_data(weekdays=weekdays)
        # Запись полученных данных в "бд" словарь flowers
        flowers.setdefault(call.from_user.id, {}).setdefault(data["flower_name"], data["weekdays"])

        await send_results(call, data, days)
        await state.clear()
    else:
        clean_data = call.data.split(":")[1]
        list_of_days.append(clean_data)


# Обработка кнопки удаления напоминаний. Пробегает по напоминаниям и формирует клавиатуру.
@router.callback_query(NotificationCallback.filter(F.action == "edit"))
async def handle_edit_notifications(call: CallbackQuery):
    if flowers[call.from_user.id]:
        builder = InlineKeyboardBuilder()
        for flower in flowers[call.from_user.id].keys():
            builder.button(
                text=flower,
                callback_data=EditNotificationCallback(flower_name=flower, action="edit").pack()
            )
        builder.adjust(1)
        await call.answer()
        await call.message.edit_text(text="Ваши напоминания:", reply_markup=builder.as_markup())
    else:
        await call.answer()
        builder = InlineKeyboardBuilder()
        builder.button(text="Добавить напоминание", callback_data=NotificationCallback(action="add").pack())
        await call.message.edit_text(
            text="Напоминания отсутствуют.\nЖелаете установить напоминание?",
            reply_markup=builder.as_markup()
        )


# Подтверждение удаления
@router.callback_query(EditNotificationCallback.filter(F.action == 'edit'))
async def handle_edit_notification(call: CallbackQuery, callback_data: EditNotificationCallback):
    flower_name = callback_data.flower_name
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Удалить!",
        callback_data=EditNotificationCallback(action="delete", flower_name=flower_name).pack()
    )
    await call.answer()
    await call.message.edit_text(
        text=f"Вы уверены, что хотите удалить напоминание для {flower_name}?",
        reply_markup=builder.as_markup(),
    )


# Собственно, удаление напоминания из "бд"
@router.callback_query(EditNotificationCallback.filter(F.action == "delete"))
async def handle_delete_notifications(call: CallbackQuery, callback_data: EditNotificationCallback):
    flower_name = callback_data.flower_name
    global flowers
    del flowers[call.from_user.id][flower_name]
    await call.answer()
    await call.message.edit_text(text="Удалено!",)

#    шедулер переделать
# scheduler.add_job(bot.send_message, 'interval', days=int(frequency),
#                   args=[message.from_user.id, f"Напоминаю полить 🌧️ {flower}"])
#
# watering = datetime.now() + timedelta(seconds=int(frequency))
# await message.answer(f"Следующий полив 💧: {datetime.strftime(watering, '%A %H:%M')}")