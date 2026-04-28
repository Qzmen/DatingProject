from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU_BROWSE = "🔎 Смотреть анкеты"
MAIN_MENU_PROFILE = "👤 Моя анкета"
MAIN_MENU_DISABLE = "⏸ Отключить анкету"
MAIN_MENU_ENABLE = "▶️ Включить анкету"

REG_GENDER_MALE = "👨 Мужчина"
REG_GENDER_FEMALE = "👩 Женщина"
REG_GENDER_OTHER = "✨ Другое"
REG_SKIP_PHOTO = "⏭ Пропустить фото"

BROWSE_LIKE = "❤️ Лайк"
BROWSE_SKIP = "➡️ Пропустить"
BROWSE_BACK_MENU = "🏠 В меню"

MEETING_CONFIRM = "✅ Подтвердить встречу"
MEETING_REJECT = "❌ Отменить встречу"
PRECHECK_YES = "🟢 Иду"
PRECHECK_NO = "🔴 Не иду"
ATTENDANCE_YES = "👍 Пришёл(ла)"
ATTENDANCE_NO = "👎 Не пришёл(ла)"


def main_menu_keyboard(profile_enabled: bool = True) -> ReplyKeyboardMarkup:
    toggle_button = MAIN_MENU_DISABLE if profile_enabled else MAIN_MENU_ENABLE
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MAIN_MENU_BROWSE), KeyboardButton(text=MAIN_MENU_PROFILE)],
            [KeyboardButton(text=toggle_button)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие в меню 👇",
    )


def registration_gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=REG_GENDER_MALE), KeyboardButton(text=REG_GENDER_FEMALE)],
            [KeyboardButton(text=REG_GENDER_OTHER)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери пол",
    )


def registration_photo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=REG_SKIP_PHOTO)]],
        resize_keyboard=True,
        input_field_placeholder="Отправь фото или нажми кнопку",
    )


def browse_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BROWSE_LIKE), KeyboardButton(text=BROWSE_SKIP)],
            [KeyboardButton(text=BROWSE_BACK_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Лайкнуть или пропустить?",
    )


def meeting_decision_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=MEETING_CONFIRM), KeyboardButton(text=MEETING_REJECT)]],
        resize_keyboard=True,
    )


def precheck_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=PRECHECK_YES), KeyboardButton(text=PRECHECK_NO)]],
        resize_keyboard=True,
    )


def attendance_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=ATTENDANCE_YES), KeyboardButton(text=ATTENDANCE_NO)]],
        resize_keyboard=True,
    )
