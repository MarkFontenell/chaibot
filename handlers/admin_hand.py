import sqlalchemy
from aiogram import Dispatcher, Bot, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.product_pages import send_products_page
from config import BotConfig
from database.models import Product, Category, Users
from states.admin_fsm import NewProduct, ProductFSM, CategoryFSM

admin_router = Router()


@admin_router.message(Command("inventory"))
async def inventory_menu(msg: Message, config: BotConfig):
    if msg.from_user.id in config.admin_ids:
        kb = [
            [types.KeyboardButton(text="➕ Добавить товар")],
            [types.KeyboardButton(text="📋 Список товаров")],
            [types.KeyboardButton(text="➕ Добавить категорию")],
            [types.KeyboardButton(text="📋 Список категорий")],
            [types.KeyboardButton(text="🗑 Удалить товар")],
            [types.KeyboardButton(text="🗑 Удалить категорию")],
        ]
        await msg.answer("📦 Меню управления товарами", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

from sqlalchemy import select
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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

    await state.update_data(price=price)

    # Получаем категории
    result = await session.execute(select(Category))
    categories = result.scalars().all()

    if not categories:
        await msg.answer("❌ Нет доступных категорий.")
        await state.clear()
        return

    # Клавиатура с категориями
    kb = InlineKeyboardBuilder()
    for category in categories:
        kb.button(text=category.name, callback_data=f"category:{category.id}")
    kb.adjust(2)

    await msg.answer("📂 Выберите категорию товара:", reply_markup=kb.as_markup())
    await state.set_state(NewProduct.product_category)

@admin_router.callback_query(NewProduct.product_category, F.data.startswith("category:"))
async def process_category_choice(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("📷 Отправьте изображение товара:")
    await state.set_state(NewProduct.product_image)
    await callback.answer()


@admin_router.message(NewProduct.product_image, F.photo)
async def add_product_image(msg: Message, state: FSMContext, session: AsyncSession):
    photo = msg.photo[-1].file_id
    data = await state.get_data()

    new_product = Product(
        name=data["name"],
        description=data["description"],
        price=data["price"],
        count=0,
        image=photo,
        category_id=data["category_id"],
    )

    session.add(new_product)
    await session.commit()

    await msg.answer("✅ Товар успешно добавлен!")
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

@admin_router.message(F.text == "➕ Добавить категорию")
async def add_category_prompt(msg: Message, state: FSMContext):
    await msg.answer("📝 Введите название новой категории:")
    await state.set_state(CategoryFSM.waiting_for_category_name)

@admin_router.message(CategoryFSM.waiting_for_category_name)
async def add_category(msg: Message, state: FSMContext, session: AsyncSession):
    name = msg.text.strip()

    if not name:
        await msg.answer("❗ Название не может быть пустым.")
        return

    session.add(Category(name=name))
    await session.commit()

    await msg.answer(f"✅ Категория <b>{name}</b> добавлена.", parse_mode="HTML")
    await state.clear()
@admin_router.message(F.text == "🗑 Удалить категорию")
async def ask_id_delete_category(msg: Message, state: FSMContext):
    await msg.answer("Введите ID категории, которую нужно удалить:")
    await state.set_state(CategoryFSM.waiting_for_category_id_to_delete)


@admin_router.message(CategoryFSM.waiting_for_category_id_to_delete, lambda m: m.text.isdigit())
async def handle_category_id_to_delete(msg: Message, state: FSMContext, session: AsyncSession):
    category_id = int(msg.text)

    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        await msg.answer("❌ Категория не найдена.")
        await state.clear()
        return

    try:
        await session.delete(category)
        await session.commit()
        await msg.answer(f"✅ Категория с ID {category_id} удалена.")
    except sqlalchemy.exc.IntegrityError:
        await session.rollback()
        await msg.answer("❌ Нельзя удалить категорию, так как к ней привязаны товары.")

    await state.clear()

@admin_router.message(F.text == "📋 Список категорий")
async def list_categories(msg: Message, session: AsyncSession):
    result = await session.execute(select(Category))
    categories = result.scalars().all()

    if not categories:
        await msg.answer("❌ Категорий пока нет.")
        return

    text = "📂 <b>Список категорий:</b>\n\n"
    for category in categories:
        text += f"🆔 <code>{category.id}</code> — {category.name}\n"

    await msg.answer(text, parse_mode="HTML")

@admin_router.message(Command("stats"))
async def stats(msg: Message, session: AsyncSession):
    result = await session.execute(select(Users))
    users = result.scalars().all()

    if not users:
        await msg.answer("📊 Пользователи не найдены.")
        return

    text = "<b>📊 Список пользователей:</b>\n\n"
    for user in users:
        text += (
            f"🆔 <b>ID:</b> {user.id}\n"
            f"👤 <b>Ник:</b> {user.nick}\n"
            f"📱 <b>Телефон:</b> {user.phone_number}\n"
            f"🪪 <b>TG ID:</b> {user.tg_id}\n"
            f"🕒 <b>Дата регистрации:</b> {user.created.strftime('%d.%m.%Y %H:%M')}\n"
            f"✅ <b>Согласие на обработку ПД:</b> {'Да' if user.consent_given else 'Нет'}\n"
        )

    if len(text) > 4096:
        # Если слишком длинное сообщение, делим по частям
        for i in range(0, len(text), 4000):
            await msg.answer(text[i:i+4000], parse_mode="HTML")
    else:
        await msg.answer(text, parse_mode="HTML")
