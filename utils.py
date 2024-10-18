from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types          import InlineKeyboardMarkup, InlineKeyboardButton

def back_button_markup(callback_data: str) -> InlineKeyboardMarkup:
    buttons = InlineKeyboardBuilder()
    buttons.button(
        text="🔙 Назад",
        callback_data=callback_data
    )
    buttons.adjust(1)
    return buttons.as_markup()

def back_button(callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="🔙 Назад",
        callback_data=callback_data
    )