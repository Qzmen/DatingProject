from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_city = State()
    waiting_photo = State()
