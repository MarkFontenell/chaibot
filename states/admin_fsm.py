from aiogram.fsm.state import StatesGroup, State

class NewProduct(StatesGroup):
    """FSM для добавления товара"""
    product_name = State()
    product_description = State()
    product_price = State()

class ProductFSM(StatesGroup):
    waiting_for_id = State()
    choosing_field = State()
    editing_value = State()