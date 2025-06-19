from aiogram import Dispatcher, Bot, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.product_pages import send_products_page
from config import BotConfig
from database.models import Product
from states.admin_fsm import NewProduct, ProductFSM
admin_router = Router()


@admin_router.message(Command("inventory"))
async def inventory_menu(msg: Message, config: BotConfig):
    if msg.from_user.id in config.admin_ids:
        kb = [
            [types.KeyboardButton(text="➕ Добавить товар")],
            [types.KeyboardButton(text="📋 Список товаров")],
            [types.KeyboardButton(text="🗑 Удалить товар")],
        ]
        await msg.answer("📦 Меню управления товарами", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

from sqlalchemy import select
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

PRODUCTS_PER_PAGE = 5

@admin_router.message(Command("products"))
@admin_router.message(F.text == "📋 Список товаров")
async def show_products_page(msg: Message, session: AsyncSession, config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await send_products_page(msg, session, page=1)

@admin_router.callback_query(F.data.startswith("page:"))
async def paginate_products(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await send_products_page(callback, session, page)


@admin_router.message(F.text == "➕ Добавить товар")
async def start_add_product(msg: Message, state: FSMContext):
    await msg.answer("📝 Введите название товара:")
    await state.set_state(NewProduct.product_name)

@admin_router.message(NewProduct.product_name)
async def add_product_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("✏ Введите описание товара:")
    await state.set_state(NewProduct.product_description)

@admin_router.message(NewProduct.product_description)
async def add_product_description(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text)
    await msg.answer("💰 Введите цену товара:")
    await state.set_state(NewProduct.product_price)

@admin_router.message(NewProduct.product_price)
async def add_product_price(msg: Message, state: FSMContext, session: AsyncSession):
    try:
        price = float(msg.text)
    except ValueError:
        await msg.answer("❗ Введите корректную цену.")
        return

    data = await state.get_data()

    new_product = Product(
        name=data["name"],
        description=data["description"],
        price=price,
        count=0,
        image="",
    )

    session.add(new_product)
    await session.commit()

    await msg.answer("✅ Товар добавлен!")
    await state.clear()

@admin_router.message(F.text == "🗑 Удалить товар")
async def ask_id_delete(msg: Message, state: FSMContext):
    await msg.answer("Введите ID товара, который нужно удалить:")
    await state.set_state(ProductFSM.waiting_for_id)
    await state.update_data(mode="delete")

@admin_router.message(ProductFSM.waiting_for_id, lambda m: m.text.isdigit())
async def handle_product_id(msg: Message, state: FSMContext, session: AsyncSession):
    product_id = int(msg.text)
    data = await state.get_data()
    mode = data.get("mode")

    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        await msg.answer("❌ Товар не найден.")
        await state.clear()
        return

    await state.update_data(product_id=product_id)

    if mode == "delete":
        await session.delete(product)
        await session.commit()
        await msg.answer(f"✅ Товар с ID {product_id} удалён.")
        await state.clear()
