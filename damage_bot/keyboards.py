from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from damage_bot.core.buttons import reminder_button_specs


def reminder_keyboard(case_id: int, category: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=button.text, callback_data=button.callback_data)
        for button in reminder_button_specs(case_id, category)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons]
    )
