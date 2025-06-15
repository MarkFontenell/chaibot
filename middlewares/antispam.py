from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any
import time

class AntiSpam(BaseMiddleware):
    def __init__(self, delsec: float = 1.5):
        self.delsec = delsec
        self.user_timestamps: dict[int, float] = {}  # ✅ создаём словарь

    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()

        # Проверка: если пользователь спамит
        if user_id in self.user_timestamps:
            elapsed = now - self.user_timestamps[user_id]
            if elapsed < self.delsec:
                await event.answer("Не так быстро, чай не вскипел ☕️")
                print(f'Пользователь {user_id} спамит!')
                return

        self.user_timestamps[user_id] = now
        return await handler(event, data)
