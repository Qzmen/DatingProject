from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_city = State()
    waiting_bio = State()
    waiting_photo = State()
    waiting_voice = State()
    waiting_video_note = State()
