from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class NotificationCallback(CallbackData, prefix="notify"):
    action: str


class WeekCallback(CallbackData, prefix="week"):
    day_of_week: str


days_of_week = {
    "понедельник": ("Пн", 0),
    "вторник": ("Вт", 1),
    "среда": ("Ср", 2),
    "четверг": ("Чт", 3),
    "пятница": ("Пт", 4),
    "суббота": ("Сб", 5),
    "воскресенье": ("Вс", 6),
}


def build_flowers_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить напоминание", callback_data=NotificationCallback(action="add").pack())
    builder.button(text="Удалить напоминаниe", callback_data=NotificationCallback(action="edit").pack())
    builder.adjust(1)
    return builder.as_markup()


def build_weekdays_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for k, v in days_of_week.items():
        builder.button(
            text=v[0],
            callback_data=WeekCallback(day_of_week=k).pack()
        )
    builder.button(
        text="Готово!",
        callback_data=WeekCallback(day_of_week='ready').pack(),
    )
    builder.adjust(7)
    return builder.as_markup()
