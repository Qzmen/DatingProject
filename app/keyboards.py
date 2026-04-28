from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_BROWSE = "🔥 Смотреть анкеты"
BTN_MATCHES = "💘 Мои матчи"
BTN_GAME = "🎮 Активная игра"
BTN_PROFILE = "👤 Мой профиль"
BTN_STOP_GAME = "🛑 Завершить игру"
BTN_SKIP = "Пропустить"
BTN_CITY_FILTER = "🌍 Фильтр по городу"


def browse_keyboard(candidate_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like:{candidate_id}"),
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip:{candidate_id}"),
        ]]
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BROWSE), KeyboardButton(text=BTN_MATCHES)],
            [KeyboardButton(text=BTN_GAME), KeyboardButton(text=BTN_PROFILE)],
            [KeyboardButton(text=BTN_CITY_FILTER), KeyboardButton(text=BTN_STOP_GAME)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие 👇",
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🙋‍♂️ Парень"), KeyboardButton(text="🙋‍♀️ Девушка")],
            [KeyboardButton(text="✨ Другое")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def incoming_like_keyboard(liker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❤️ Лайкнуть в ответ", callback_data=f"like_back:{liker_id}"),
            InlineKeyboardButton(text="❌ Пропустить", callback_data=f"pass_like:{liker_id}"),
        ]]
    )


def match_keyboard(match_id: int, status: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if status in {"matched", "game_declined"}:
        rows.append([InlineKeyboardButton(text="🎲 Предложить игру знакомства", callback_data=f"propose_game:{match_id}")])
    if status == "game_active":
        rows.append([InlineKeyboardButton(text="▶️ Продолжить игру", callback_data=f"continue_game:{match_id}")])
        rows.append([InlineKeyboardButton(text="🔓 Предложить раскрыть контакт", callback_data=f"reveal_contact:{match_id}")])
    rows.append([InlineKeyboardButton(text="❌ Закрыть матч", callback_data=f"close_match:{match_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def game_invite_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_game:{match_id}"),
        InlineKeyboardButton(text="❌ Отказаться", callback_data=f"decline_game:{match_id}"),
    ]])


def game_round_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🫶 Парный челлендж дня", callback_data=f"daily_challenge:{match_id}")],
        [InlineKeyboardButton(text="🎲 Игра в кубик", callback_data=f"dice_game:{match_id}")],
        [InlineKeyboardButton(text="🔥 Следующий раунд", callback_data=f"next_round:{match_id}")],
        [InlineKeyboardButton(text="🔓 Предложить раскрыть контакт", callback_data=f"reveal_contact:{match_id}")],
        [InlineKeyboardButton(text="❌ Завершить игру", callback_data=f"close_match:{match_id}")],
    ])


def challenge_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Челлендж выполнен", callback_data=f"complete_challenge:{match_id}")],
            [InlineKeyboardButton(text="🔄 Новый челлендж", callback_data=f"daily_challenge:{match_id}")],
        ]
    )


def contact_reveal_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, раскрыть контакт", callback_data=f"accept_reveal:{match_id}"),
        InlineKeyboardButton(text="❌ Нет, продолжить игру", callback_data=f"decline_reveal:{match_id}"),
    ]])


def match_list_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{m['partner_name']} • {m['status_ru']}", callback_data=f"match:{m['id']}")] for m in matches[:20]]
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Пусто", callback_data="noop")]])
