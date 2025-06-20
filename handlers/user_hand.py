from random import choice, random
from aiogram import Dispatcher, Bot, types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold, hitalic
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Users, Product
from message.user_message import welcome_messages, long_name_responses, returning_welcome_messages
from states.user_fsm import Registration
from keyboards.user_keyboard import start_button, request_phone_keyboard, consent_keyboard, user_main_keyboard
from config import BotConfig

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(msg: Message, config: BotConfig, session: AsyncSession) -> None:
    if msg.from_user.id not in config.admin_ids:

        result = await session.execute(select(Users).where(Users.tg_id == msg.from_user.id))
        user = result.scalars().first()
        if user:
            text = choice(returning_welcome_messages).format(name=user.nick)
            await msg.answer(text, reply_markup=user_main_keyboard)
        else:
            await msg.answer(config.welcome_message, reply_markup=start_button)
    else:
        await msg.answer(f"{hbold('Добро пожаловать, администратор!')} 👑\n\n"
                         "Вы вошли в панель управления ботом ZATLAN TEA 🍃.\n\n"
                         "Вот что доступно вам:\n"
                         "🔹 Управление заказами\n"
                         "🔹 Обновление ассортимента чая\n"
                         "🔹 Просмотр статистики и отчётов\n"
                         "🔹 Ответы на вопросы пользователей\n\n"
                         "Используйте команды, чтобы быстро и эффективно управлять ботом:\n"
                         "/orders - посмотреть все заказы\n"
                         "/inventory - обновить ассортимент\n"
                         "/stats - получить статистику бота\n\n"
                         "✨ Спасибо за управление ZATLAN TEA! 🍵"
                         )


@user_router.callback_query(F.data == "start_journey")
async def start_registration(callback: types.CallbackQuery, state: FSMContext) :
    await callback.message.delete()

    await callback.message.answer(choice(welcome_messages))
    await state.set_state(Registration.name)
    await callback.answer()

# Принимаем имя и спрашиваем номер
@user_router.message(Registration.name)
async def get_name(msg: types.Message, state: FSMContext):
    name = msg.text.strip()

    if len(name) > 30:
        await msg.answer(choice(long_name_responses))
        return

    await state.update_data(name=name)
    # Запрашиваем согласие
    await msg.answer(
        f"Отлично, {name}! 🍃\n"
        "Перед тем как продолжить, пожалуйста, согласись на обработку персональных данных.",
        reply_markup=consent_keyboard
    )
    await state.set_state(Registration.consent_given)


# Принимаем согласие
@user_router.message(Registration.consent_given)
async def get_consent(msg: types.Message, state: FSMContext):
    if msg.text != "Согласен на обработку персональных данных":
        await msg.answer("Для продолжения регистрации нужно согласиться на обработку персональных данных.")
        return
    await state.update_data(consent_given=True)

    # После согласия запрашиваем номер телефона
    await msg.answer(
        "Спасибо! Теперь, пожалуйста, отправь свой номер телефона, нажав кнопку ниже 📲",
        reply_markup=request_phone_keyboard
    )
    await state.set_state(Registration.number)


# Принимаем номер телефона и завершаем регистрацию (как у тебя)
@user_router.message(Registration.number, F.contact)
async def get_contact(msg: types.Message, state: FSMContext, session : AsyncSession):
    data = await state.get_data()
    name = data.get("name")
    tg_id = msg.from_user.id
    phone = msg.contact.phone_number
    print(phone)
    consent = data.get("consent_given", False)

    obj = Users(
        nick = name,
        tg_id = tg_id,
        phone_number = phone,
        consent_given = consent,)

    session.add(obj)
    await session.commit()


    # Здесь сохраняем в базу: name, tg_id, phone и consent

    await msg.answer(
        f"Регистрация завершена! 🎉\n\n"
        f"{hbold(f'Добро пожаловать в клуб ZATLAN TEA, {name}!')} 🍵\n"
        "Теперь тебе доступны бонусы, реферальная система и уникальные предложения.\n"
        "Желаем ароматных открытий и уютных чайных моментов 🌿✨",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()

@user_router.message(F.text == '❓ FAQ')
async def FAQ(msg: Message):
    await msg.answer(
        "🍵 *Часто задаваемые вопросы о нашем чайном магазине:*\n\n"
        "🔹 *Что делает этот бот?*\n"
        "Бот помогает вам получать карту покупателя, следить за бонусами и участвовать в акциях нашего чайного магазина.\n\n"
        "🔹 *Как получить карту покупателя?*\n"
        "Нажмите «Регистрация» и отправьте свой номер телефона. После этого вы получите QR-код — это и есть ваша карта.\n\n"
        "🔹 *Как пользоваться картой?*\n"
        "Покажите QR-код продавцу при покупке. Он отсканирует его, и вам начислятся бонусы.\n\n"
        "🔹 *Как списать бонусы?*\n"
        "Скажите продавцу, что хотите оплатить бонусами — он отсканирует вашу карту и спишет нужную сумму.\n\n"
        "🔹 *Что делать, если потерял QR-код?*\n"
        "Просто снова авторизуйтесь по номеру телефона — бот пришлёт вам вашу карту заново.\n\n"
        "Если остались вопросы — пишите нам в поддержку! ☕",
        parse_mode="Markdown"
    )

@user_router.message(F.text == '📞Контакты')
async def contacts(msg: Message):
    await msg.answer(
        "📞 *Контакты нашего чайного магазина:*\n\n"
        "🏬 *Адрес магазина:*\n"
        "г. Челябинск, ул. Пушкина, 1\n\n"
        "📱 *Телефон:*\n"
        "+7 (999) 999-99-99\n\n"
        "💬 *Telegram для связи:*\n"
        "[@Pisya_popa09]\n\n"
        "🕒 *Часы работы:*\n"
        "Пн–Сб: 10:00–20:00\n"
        "Вс: выходной\n\n"
        "Если у вас есть вопросы — мы всегда на связи! ☕",
        parse_mode="Markdown"
    )

@user_router.message(F.text == '⚙️ Профиль')
async def profile(msg: Message, session: AsyncSession):
    result = await session.execute(
        select(Users).where(Users.tg_id == msg.from_user.id)
    )
    user = result.scalar_one_or_none()

    if user:
        await msg.answer(
            text=(
                "🧾 <b>Профиль пользователя</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Ник:</b> <code>{user.nick}</code>\n"
                f"📱 <b>Телефон:</b> <code>{user.phone_number}</code>\n"
                f"🗓 <b>Регистрация:</b> <code>{user.created.strftime('%d.%m.%Y %H:%M')}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode='HTML'
        )
    else:
        await msg.answer("❌ Пользователь не найден. Вы зарегистрированы?")

@user_router.message(F.text == '📋 Меню')
async def show_menu(msg: Message, session: AsyncSession):
    products = await session.execute(select(Product))
    products = products.scalars().all()

    if not products:
        await msg.answer("😔 Сейчас в магазине нет товаров.")
        return

    chunks = []
    text = ""
    for i, product in enumerate(products, 1):
        description = product.description or "—"
        text += (
            f"<b>{i}. {product.name}</b>\n"
            f"💰 <b>Цена:</b> {int(product.price)} ₽\n"
            f"📦 <b>В наличии:</b> {product.count} шт.\n"
            f"🆔 <b>ID:</b> {product.id}\n"
            f"📝 <b>Описание:</b> {description}\n\n"
        )
        if len(text) > 3500:
            chunks.append(text)
            text = ""
    chunks.append(text)

    for part in chunks:
        await msg.answer(part, parse_mode="HTML")
