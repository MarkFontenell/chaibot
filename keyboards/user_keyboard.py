from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

start_button = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚀 Начать путешествие", callback_data="start_journey")]
])

request_phone_keyboard = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="📲 Отправить номер телефона", request_contact=True)]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)