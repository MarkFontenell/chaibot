import asyncio
from bot_instance import bot
from aiogram import Bot, Dispatcher

from config import BotConfig
from handlers.admin_hand import admin_router
from handlers.user_hand import user_router
from aiogram.utils.markdown import hbold
from middlewares.antispam import AntiSpam

def register_routers(dp: Dispatcher) -> None:
    dp.include_router(user_router)
    dp.include_router(admin_router)


async def main(bot: Bot) -> None:
    dp = Dispatcher()
    dp.message.middleware(AntiSpam(delsec=0.5))  # можно изменить интервал
    dp.callback_query.middleware(AntiSpam(delsec=0.5))
    config = BotConfig(
        admin_ids=[209963062],
        welcome_message=(
            f"{hbold('Добро пожаловать в ZATLAN TEA!')} 🍃\n\n"
            f"Вы попали в место, где живут самые {hbold('вкусные и ароматные чаи')} со всего мира.\n"
            f"Каждый сорт — это история, настроение и маленькое путешествие. 🍵\n\n"
            f"🔸 Не знаете, какой чай выбрать? Мы с радостью подскажем! 🌿\n"
            f"🔸 Хотите узнать секреты заваривания? В боте вас ждут советы и рецепты! ☕️\n\n"
            f"{hbold('Готовы начать чайное путешествие?')} 🌍✨"
        )
    )
    dp['config'] = config
    register_routers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main(bot))