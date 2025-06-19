from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Product

PRODUCTS_PER_PAGE = 5

async def send_products_page(msg_or_cb: Message | CallbackQuery, session: AsyncSession, page: int):
    result = await session.execute(select(Product).order_by(Product.created.desc()))
    products = result.scalars().all()

    total = len(products)
    if total == 0:
        await msg_or_cb.answer("❌ Товары не найдены.")
        return

    start = (page - 1) * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    current_products = products[start:end]

    text = ""
    for product in current_products:
        text += (
            f"🛒 <b>{product.name}</b>\n"
            f"🆔 <i>ID:</i> <code>{product.id}</code>\n"
            f"💵 <i>Цена:</i> {int(product.price)} ₽\n"
            f"📦 <i>В наличии:</i> {product.count} шт.\n"
            f"🖼 <i>Изображение:</i> {product.image or '—'}\n"
            f"{'—' * 30}\n\n"
        )

    # Кнопки пагинации
    kb = InlineKeyboardBuilder()
    if page > 1:
        kb.button(text="⬅ Назад", callback_data=f"page:{page - 1}")
    if end < total:
        kb.button(text="➡ Вперёд", callback_data=f"page:{page + 1}")
    kb.adjust(2)

    if isinstance(msg_or_cb, Message):
        await msg_or_cb.answer(text.strip(), reply_markup=kb.as_markup())
    else:
        await msg_or_cb.message.edit_text(text.strip(), reply_markup=kb.as_markup())
        await msg_or_cb.answer()
