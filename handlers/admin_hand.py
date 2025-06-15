from aiogram import Dispatcher, Bot, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold

from config import BotConfig

admin_router = Router()

@admin_router.message(Command('inventory'))
async def inventory(msg: Message, config: BotConfig) -> None:
    if msg.from_user.id in config.admin_ids:
        await msg.answer('Вы зашли в меню добавления товара')

@admin_router.message(Command('stats'))
async def stats(msg: Message, config: BotConfig) -> None:
    if msg.from_user.id in config.admin_ids:
        await msg.answer('Вы зашли в меню статистики')

@admin_router.message(Command('orders'))
async def orders(msg: Message, config: BotConfig) -> None:
    if msg.from_user.id in config.admin_ids:
        await msg.answer('Вы зашли в меню заказов')

