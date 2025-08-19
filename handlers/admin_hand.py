import sqlalchemy
from aiogram import Dispatcher, Bot, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from handlers.user_hand import user_router
from utils.admin_pages import send_admin_page, send_orders_page
from utils.product_pages import send_products_page
from config import BotConfig
from database.models import Product, Category, Users, Order, Cart, OrderItem
from states.admin_fsm import NewProduct, ProductFSM, CategoryFSM
import pandas as pd
import tempfile
from aiogram.utils.keyboard import InlineKeyboardBuilder
admin_router = Router()

@admin_router.message(Command("inventory"))
async def inventory_menu(msg: Message, config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    if msg.from_user.id not in config.admin_ids:
        return
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
    await send_admin_page(msg, session, page_ad=1)

@admin_router.callback_query(F.data.startswith("page_ad:"))
async def paginate_products(callback: CallbackQuery, session: AsyncSession, config: BotConfig):
    if callback.from_user.id not in config.admin_ids:
        await callback.answer("❌ Недостаточно прав.", show_alert=True)
        return
    page = int(callback.data.split(":")[1])
    await send_admin_page(callback, session, page)

@admin_router.message(F.text == "➕ Добавить товар")
async def start_add_product(msg: Message, state: FSMContext, config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await msg.answer("📝 Введите название товара:")
    await state.set_state(NewProduct.product_name)

@admin_router.message(NewProduct.product_name)
async def add_product_name(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await state.update_data(name=msg.text)
    await msg.answer("✏ Введите описание товара:")
    await state.set_state(NewProduct.product_description)

@admin_router.message(NewProduct.product_description)
async def add_product_description(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await state.update_data(description=msg.text)
    await msg.answer("📦  Введите кол-во товара на складе:")
    await state.set_state(NewProduct.product_count)

@admin_router.message(NewProduct.product_count)
async def add_product_price(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    try:
        count = abs(float(msg.text))
    except ValueError:
        await msg.answer("❗ Введите корректное число.")
        return

    await state.update_data(count=count)
    await msg.answer("💰 Введите цену товара:")
    await state.set_state(NewProduct.product_price)

@admin_router.message(NewProduct.product_price)
async def add_product_price(msg: Message, state: FSMContext, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    try:
        price = abs(float(msg.text))
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
async def process_category_choice(callback: CallbackQuery, state: FSMContext,config: BotConfig):
    if callback.from_user.id not in config.admin_ids:
        await callback.answer("❌ Недостаточно прав.", show_alert=True)
        return
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("📷 Отправьте изображение товара:")
    await state.set_state(NewProduct.product_image)
    await callback.answer()


@admin_router.message(NewProduct.product_image, F.photo)
async def add_product_image(msg: Message, state: FSMContext, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    photo = msg.photo[-1].file_id
    data = await state.get_data()

    new_product = Product(
        name=data["name"],
        description=data["description"],
        price=data["price"],
        count=data["count"],
        image=photo,
        category_id=data["category_id"],
    )

    session.add(new_product)
    await session.commit()

    await msg.answer("✅ Товар успешно добавлен!")
    await state.clear()



@admin_router.message(F.text == "🗑 Удалить товар")
async def ask_id_delete(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return

    await msg.answer("Введите ID товара, который нужно удалить:")
    await state.set_state(ProductFSM.waiting_for_id)
    await state.update_data(mode="delete")

@admin_router.message(ProductFSM.waiting_for_id, lambda m: m.text.isdigit())
async def handle_product_id(msg: Message, state: FSMContext, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
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
async def add_category_prompt(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await msg.answer("📝 Введите название новой категории:")
    await state.set_state(CategoryFSM.waiting_for_category_name)

@admin_router.message(CategoryFSM.waiting_for_category_name)
async def add_category(msg: Message, state: FSMContext, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    name = msg.text.strip()

    if not name:
        await msg.answer("❗ Название не может быть пустым.")
        return

    session.add(Category(name=name))
    await session.commit()

    await msg.answer(f"✅ Категория <b>{name}</b> добавлена.", parse_mode="HTML")
    await state.clear()
@admin_router.message(F.text == "🗑 Удалить категорию")
async def ask_id_delete_category(msg: Message, state: FSMContext,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await msg.answer("Введите ID категории, которую нужно удалить:")
    await state.set_state(CategoryFSM.waiting_for_category_id_to_delete)


@admin_router.message(CategoryFSM.waiting_for_category_id_to_delete, lambda m: m.text.isdigit())
async def handle_category_id_to_delete(msg: Message, state: FSMContext, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
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
async def list_categories(msg: Message, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    result = await session.execute(select(Category))
    categories = result.scalars().all()

    if not categories:
        await msg.answer("❌ Категорий пока нет.")
        return

    text = "📂 <b>Список категорий:</b>\n\n"
    for category in categories:
        text += f"🆔 <code>{category.id}</code> — {category.name}\n"

    await msg.answer(text, parse_mode="HTML")


@admin_router.message(Command("orders"))
async def orders(msg : Message, session: AsyncSession, config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    await send_orders_page(msg.chat.id, session, page=1, bot=msg.bot)

@admin_router.callback_query(F.data.startswith("open_orders_page:"))
async def open_orders_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    await callback.message.delete()
    await send_orders_page(callback.message.chat.id, session, page, callback.bot)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("view_order:"))
async def view_order(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    page = int(parts[3]) if len(parts) > 3 else 1

    order = await session.get(Order, order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    await session.refresh(order, ["items", "user"])
    text = f"<b>📦 Заказ #{order.id}</b>\n"
    text += f"👤 Покупатель: {order.user.nick}, {order.user.phone_number}\n"
    text += f"💰 Сумма: {order.total_amount} ₽\n"
    text += f"💳 Оплата: {order.payment_method}\n"
    text += f"📅 Дата: {order.created.strftime('%d.%m.%Y %H:%M')}\n"
    text += f"✅ Оплачен: {'Да' if order.is_paid else 'Нет'}\n"
    text += f"📤 Выдан: {'Да' if order.is_issued else 'Нет'}\n"
    text += f"🧾 Подтвержден клиентом: {'Да' if order.user_confirmed else 'Нет'}\n\n"

    text += "<b>🧺 Товары:</b>\n"
    for item in order.items:
        await session.refresh(item, ["product"])
        text += f"• {item.product.name} — {item.quantity} шт.\n"

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    if not order.is_paid:
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment:{order.id}:page:{page}")
        ])
    elif not order.is_issued:
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text="📤 Подтвердить выдачу", callback_data=f"confirm_issue:{order.id}:page:{page}")
        ])

    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"open_orders_page:{page}")
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("confirm_payment:"))
async def confirm_payment(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    page = int(parts[3])

    order = await session.get(Order, order_id)
    if not order:
        await callback.answer("Заказ не найден.")
        return

    order.is_paid = True
    await session.commit()
    await view_order(callback, session)  # Обновим заказ

@admin_router.callback_query(F.data.startswith("confirm_issue:"))
async def confirm_issue(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    page = int(parts[3]) if len(parts) > 3 else 1

    order = await session.get(Order, order_id)
    if not order:
        await callback.answer("Заказ не найден.")
        return

    order.is_issued = True
    await session.commit()

    user = await session.get(Users, order.user_id)
    if user:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_user:{order.id}")
        ]])
        await callback.bot.send_message(
            user.tg_id,
            "📦 Ваш заказ выдан. Пожалуйста, подтвердите, что вы его получили.",
            reply_markup=keyboard
        )

    await view_order(callback, session)

@user_router.callback_query(F.data.startswith("confirm_user:"))
async def confirm_user(callback: CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    order = await session.get(Order, order_id)

    if not order:
        await callback.answer("Заказ не найден.")
        return

    order.user_confirmed = True
    await session.commit()
    await callback.message.edit_text("✅ Спасибо! Вы подтвердили получение заказа.")
    await callback.answer()

@admin_router.message(Command("stats"))
async def stats(msg: Message, session: AsyncSession,config: BotConfig):
    if msg.from_user.id not in config.admin_ids:
        return
    result = await session.execute(select(Users))
    users = result.scalars().all()

    if not users:
        await msg.answer("❌ Пользователи не найдены.")
        return

    data = []
    for user in users:
        data.append({
            "ID": user.id,
            "Ник": user.nick,
            "TG ID": user.tg_id,
            "Телефон": user.phone_number,
            "Дата регистрации": user.created.strftime("%d.%m.%Y %H:%M")
        })

    df = pd.DataFrame(data)



    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name


    with pd.ExcelWriter(tmp_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Users")


    file = FSInputFile(tmp_path, filename="Клиенты.xlsx")

    await msg.answer_document(file, caption="📄 Список клиентов в Excel")

    import os
    os.remove(tmp_path)

