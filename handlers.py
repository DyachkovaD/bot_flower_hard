import json
import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram import BaseMiddleware, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery
from aiogram.utils import markdown
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from keyboards import NotificationCallback, build_weekdays_kb, days_of_week

router = Router()
scheduler = AsyncIOScheduler(timezone='Europe/Moscow')


def load_data():
    try:
        with open('flowers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_data():
    with open('flowers.json', 'w') as f:
        json.dump(flowers, f, ensure_ascii=False, indent=4)


flowers = load_data()
list_of_days = []


class Notification(StatesGroup):
    flower_name = State()
    weekdays = State()


class EditNotification(StatesGroup):
    flower_name = State()
    weekdays = State()
    old_flower_name = State()


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
    user_id = str(message.from_user.id)
    text = "Управление напоминаниями:"
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить напоминание", callback_data=NotificationCallback(action="add").pack())
    if user_id in flowers.keys():
        builder.button(text="Изменить напоминаниe", callback_data=NotificationCallback(action="edit").pack())
        builder.button(text="Удалить напоминаниe", callback_data=NotificationCallback(action="delete").pack())
    builder.adjust(1)
    await message.answer(text=text, reply_markup=builder.as_markup())


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
        "Напоминание добавлено:"
        "",
        markdown.text("Наименование растения: ", markdown.hbold(data["flower_name"])),
        markdown.text(f"Выбранные дни полива: {markdown.hbold(days)}\n"
                      f"Для управления напоминаниями введите /flowers"),
        sep='\n',
    )
    await call.message.edit_text(text=text)


# Обработка выбранных дней недели.
@router.callback_query(Notification.weekdays, lambda call: True)
async def handle_days_of_week(call: CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    global list_of_days
    global flowers
    if call.data == "week:ready":
        days = ", ".join(list_of_days)
        weekdays = [days_of_week[x][1] for x in list_of_days]
        list_of_days = []
        data = await state.update_data(weekdays=weekdays)
        # Запись полученных данных в "бд" словарь flowers
        flowers.setdefault(user_id, {}).setdefault(data["flower_name"], data["weekdays"])
        save_data()

        await send_results(call, data, days)
        await state.clear()

        # Добавление в расписание
        days = flowers[user_id].get(data['flower_name'])
        now = datetime.now().weekday()
        days_to_next_water = [x - now if x > now else (7 - now + x) for x in days]
        for i in range(len(days_to_next_water)):
            start_date = datetime.now() + timedelta(days=days_to_next_water[i])
            scheduler.add_job(call.message.answer, 'interval', days=7, start_date=start_date,
                              args=[f"Напоминаю полить 🌧️ {data['flower_name']}"],
                              id=f"{data['flower_name']}_{days[i]}")    # id = "Фиалка_3"
    else:
        if call.data.split(":")[1] in list_of_days:
            list_of_days.remove(call.data.split(":")[1])
        else:
            clean_data = call.data.split(":")[1]
            list_of_days.append(clean_data)
    print(flowers)


# Обработка кнопки изменения напоминаний. Пробегает по напоминаниям и формирует клавиатуру.
@router.callback_query(NotificationCallback.filter(F.action == "edit"))
async def handle_edit_notifications(call: CallbackQuery):
    user_id = str(call.from_user.id)
    builder = InlineKeyboardBuilder()
    for flower in flowers[user_id].keys():
        builder.button(
            text=flower,
            callback_data=EditNotificationCallback(flower_name=flower, action="edit").pack()
        )
    builder.adjust(1)
    await call.answer()
    await call.message.edit_text(text="Ваши напоминания:", reply_markup=builder.as_markup())


# Обработка изменения напоминания
@router.callback_query(EditNotificationCallback.filter(F.action == 'edit'))
async def handle_edit_notification(call: CallbackQuery, callback_data: EditNotificationCallback):
    flower_name = callback_data.flower_name
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Изменить наименование растения",
        callback_data=EditNotificationCallback(action="edit_flower_name", flower_name=flower_name).pack()
    )
    builder.button(
        text="Изменить дни полива",
        callback_data=EditNotificationCallback(action="edit_weekdays", flower_name=flower_name).pack()
    )
    builder.adjust(1)
    await call.answer()
    await call.message.edit_text(
        text=f"Вы хотите изменить наименование или дни полива для растения {markdown.hbold(flower_name)}?",
        reply_markup=builder.as_markup(),
    )


# Запуск опроса на изменение наименования растения
@router.callback_query(EditNotificationCallback.filter(F.action == "edit_flower_name"))
async def handle_edit_notification_name(call: CallbackQuery, callback_data: EditNotificationCallback, state: FSMContext):
    old_flower_name = callback_data.flower_name
    await call.answer()
    await state.set_state(EditNotification.old_flower_name)
    await state.update_data(old_flower_name=old_flower_name)
    await state.set_state(EditNotification.flower_name)
    await call.message.edit_text(
        text="Напишите новое название растения.\n"
             "Для отмены введите /cancel",
    )


# Продолжение опроса на изменение наименования растения
@router.message(EditNotification.flower_name)
async def handle_rename_notification(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Некорректный ввод. Пожалуйста, введите наименование растения",)
        return
    data = await state.update_data(flower_name=message.text)
    user_id = str(message.from_user.id)
    old_flower_name = data["old_flower_name"]
    new_flower_name = data["flower_name"]
    days = flowers[user_id].get(data["old_flower_name"])
    flowers[user_id].pop(old_flower_name)
    flowers[user_id][new_flower_name] = days
    save_data()

    # Удаление всех задач с цветком, который изменяем
    # for job in scheduler.get_jobs():
    #     if job.id.startswith(old_flower_name):
    #         scheduler.remove_job(job.id)

    # Добавление в расписание
    # days = flowers[user_id].get(data['flower_name'])
    # now = datetime.now().weekday()
    # days_to_next_water = [x - now if x > now else (7 - now + x) for x in days]
    # for i in range(len(days_to_next_water)):
    #     start_date = datetime.now() + timedelta(days=days_to_next_water[i])
    #     scheduler.add_job(message.answer, 'interval', days=7, start_date=start_date,
    #                       args=[f"Напоминаю полить 🌧️ {data['flower_name']}"],
    #                       id=f"{data['flower_name']}_{days[i]}")  # id = "Фиалка_3"

    await state.clear()
    await message.answer(
        f"Наименование напоминания с {markdown.hbold(old_flower_name)} изменено на {markdown.hbold(new_flower_name)}",
    )
    print(flowers)


# Запуск опроса на изменение дней полива
@router.callback_query(EditNotificationCallback.filter(F.action == "edit_weekdays"))
async def handle_edit_notification_days(call: CallbackQuery, callback_data: EditNotificationCallback, state: FSMContext):
    flower_name = callback_data.flower_name
    await call.answer()
    await state.set_state(EditNotification.flower_name)
    await state.update_data(flower_name=flower_name)
    await state.set_state(EditNotification.weekdays)
    await call.message.edit_text(
        text=f"Вы редактируете дни напоминаний для полива растения: {flower_name}.\n"
             f"Выберите новые дни недели для полива. Определившись с выбором, нажмите 'Готово!'\n"
             f"Для отмены введите /cancel",
        reply_markup=build_weekdays_kb()
    )


# Продолжение опроса на изменение дней полива.
@router.callback_query(EditNotification.weekdays, lambda call: True)
async def handle_new_notification_days(call: CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    global list_of_days
    global flowers
    if call.data == "week:ready":
        days = ", ".join(list_of_days)
        weekdays = [days_of_week[x][1] for x in list_of_days]
        list_of_days = []
        data = await state.update_data(weekdays=weekdays)
        flowers[user_id][data["flower_name"]] = data["weekdays"]
        save_data()

        await send_results(call, data, days)
        await state.clear()

        # Корректировка расписания
        # days = flowers[user_id].get(data['flower_name'])
        # now = datetime.now().weekday()
        # days_to_next_water = [x - now if x > now else (7 - now + x) for x in days]
        # for i in range(len(days_to_next_water)):
        #     start_date = datetime.now() + timedelta(days=days_to_next_water[i])
        #     scheduler.add_job(call.message.answer, 'interval', days=7, start_date=start_date,
        #                       args=[f"Напоминаю полить 🌧️ {data['flower_name']}"],
        #                       id=f"{data['flower_name']}_{days[i]}")    # id = "Фиалка_3"
    else:
        if call.data.split(":")[1] in list_of_days:
            list_of_days.remove(call.data.split(":")[1])
        else:
            clean_data = call.data.split(":")[1]
            list_of_days.append(clean_data)
    print(flowers)


# Обработка кнопки удаления напоминаний. Пробегает по напоминаниям и формирует клавиатуру.
@router.callback_query(NotificationCallback.filter(F.action == "delete"))
async def handle_delete_notifications(call: CallbackQuery):
    user_id = str(call.from_user.id)
    builder = InlineKeyboardBuilder()
    for flower in flowers[user_id].keys():
        builder.button(
            text=flower,
            callback_data=EditNotificationCallback(flower_name=flower, action="delete").pack()
        )
    builder.adjust(1)
    await call.answer()
    await call.message.edit_text(text="Ваши напоминания:", reply_markup=builder.as_markup())


# Подтверждение удаления
@router.callback_query(EditNotificationCallback.filter(F.action == 'delete'))
async def handle_accept_delete_notification(call: CallbackQuery, callback_data: EditNotificationCallback):
    flower_name = callback_data.flower_name
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Удалить!",
        callback_data=EditNotificationCallback(action="accept_delete", flower_name=flower_name).pack()
    )
    await call.answer()
    await call.message.edit_text(
        text=f"Вы уверены, что хотите удалить напоминание для {flower_name}?",
        reply_markup=builder.as_markup(),
    )


# Собственно, удаление напоминания из "бд"
@router.callback_query(EditNotificationCallback.filter(F.action == "accept_delete"))
async def handle_delete_notification(call: CallbackQuery, callback_data: EditNotificationCallback):
    user_id = str(call.from_user.id)
    flower_name = callback_data.flower_name
    global flowers

    # Удаление всех задач с цветком, который удаляем
    for job in scheduler.get_jobs():
        if job.id.startswith(flower_name):
            scheduler.remove_job(job.id)

    del flowers[user_id][flower_name]
    save_data()
    await call.answer()
    await call.message.edit_text(text="Удалено!",)

