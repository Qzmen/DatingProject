from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

BTN_BROWSE = "🔍 Смотреть анкеты"
BTN_BOTTLE = "🎮 Играть в бутылочку"
BTN_MATCHES = "💞 Мои матчи"
BTN_PROFILE = "👤 Моя анкета"
BTN_SETTINGS = "⚙️ Настройки"
BTN_BACK = "◀️ Назад"
BTN_SKIP = "Пропустить"
BTN_CITY_FILTER = "🌍 Фильтр по городу"
BTN_START_REG = "Начать регистрацию"
BTN_EDIT_PROFILE = "✏️ Редактировать анкету"
BTN_DELETE_PROFILE_ELEMENT = "🗑 Удалить элемент"
BTN_EDIT_NAME = "📝 Имя"
BTN_EDIT_AGE = "🔢 Возраст"
BTN_EDIT_CITY = "🏙 Город"
BTN_EDIT_BIO = "📖 Описание"
BTN_EDIT_PHOTO = "🖼 Фото"
BTN_EDIT_VOICE = "🎤 Голосовое"
BTN_EDIT_VIDEO_NOTE = "🎥 Кружок"
BTN_DELETE_BIO = "🗑 Удалить описание"
BTN_DELETE_PHOTO = "🗑 Удалить фото"
BTN_DELETE_VOICE = "🗑 Удалить голосовое"
BTN_DELETE_VIDEO_NOTE = "🗑 Удалить кружок"

BTN_END_GAME = "❌ Завершить игру"
BTN_REFRESH = "🔄 Обновить статус"
BTN_BROWSE_REFRESH = "🔄 Обновить"
BTN_NEXT_ROUND = "🔥 Следующий раунд"
BTN_REVEAL_CONTACT = "🔓 Раскрыть контакт"
BTN_ADDITIONAL = "🎲 Дополнительно"
BTN_CHALLENGE = "🎯 Челлендж дня"
BTN_DICE = "🎲 Игра в кубик"

BTN_MATCH_PROPOSE = "🎲 Предложить игру"
BTN_MATCH_CONTINUE = "▶️ Продолжить игру"
BTN_MATCH_REVEAL = "🔓 Раскрыть контакт"
BTN_MATCH_CLOSE = "❌ Закрыть матч"
BTN_MATCH_WAIT = "⏳ Ждём ответа"
BTN_MATCH_SHOW_CONTACT = "👤 Показать контакт"
BTN_MATCH_REBROWSE = "🔍 Смотреть анкету снова"
BTN_MATCH_REMOVE = "❌ Убрать из списка"
BTN_BOTTLE_LIST = "📋 Лобби города"
BTN_BOTTLE_CREATE = "➕ Создать лобби"
BTN_BOTTLE_JOIN_CODE = "🔑 Войти по коду"
BTN_BOTTLE_START = "▶️ Запустить лобби"
BTN_BOTTLE_SPIN = "🌀 Крутить бутылочку"
BTN_BOTTLE_LEAVE = "🚪 Выйти из лобби"


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
            [KeyboardButton(text=BTN_BOTTLE), KeyboardButton(text=BTN_MATCHES)],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_BROWSE)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def game_waiting_answer_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_END_GAME)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Отправь ответ сообщением",
    )


def game_waiting_partner_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_REFRESH), KeyboardButton(text=BTN_END_GAME)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Ждём ответ партнёра",
    )


def browse_empty_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BROWSE_REFRESH)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Обновить подбор",
    )


def bottle_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOTTLE_LIST), KeyboardButton(text=BTN_BOTTLE_CREATE)],
            [KeyboardButton(text=BTN_BOTTLE_JOIN_CODE)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери лобби",
    )


def bottle_lobby_keyboard(is_host: bool) -> ReplyKeyboardMarkup:
    rows = []
    if is_host:
        rows.append([KeyboardButton(text=BTN_BOTTLE_START)])
        rows.append([KeyboardButton(text=BTN_BOTTLE_SPIN)])
    rows.append([KeyboardButton(text=BTN_BOTTLE_LEAVE), KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Лобби")


def game_round_finished_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEXT_ROUND), KeyboardButton(text=BTN_REVEAL_CONTACT)],
            [KeyboardButton(text=BTN_ADDITIONAL), KeyboardButton(text=BTN_END_GAME)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Раунд завершён",
    )


def match_actions_keyboard(status: str) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    if status in {"matched", "game_declined"}:
        rows.append([KeyboardButton(text=BTN_MATCH_PROPOSE)])
    elif status == "game_invited":
        rows.append([KeyboardButton(text=BTN_MATCH_WAIT)])
    elif status == "game_active":
        rows.append([KeyboardButton(text=BTN_MATCH_CONTINUE), KeyboardButton(text=BTN_MATCH_REVEAL)])
        rows.append([KeyboardButton(text=BTN_MATCH_CLOSE)])
    elif status == "contact_revealed":
        rows.append([KeyboardButton(text=BTN_MATCH_SHOW_CONTACT), KeyboardButton(text=BTN_MATCH_REBROWSE)])
    elif status == "closed":
        rows.append([KeyboardButton(text=BTN_MATCH_REBROWSE), KeyboardButton(text=BTN_MATCH_REMOVE)])
    elif status == "game_ended":
        rows.append([KeyboardButton(text=BTN_MATCH_REBROWSE), KeyboardButton(text=BTN_MATCH_REMOVE)])
    else:
        rows.append([KeyboardButton(text=BTN_MATCH_CLOSE)])
    if status not in {"contact_revealed", "closed", "game_active"}:
        rows.append([KeyboardButton(text=BTN_MATCH_CLOSE)])
    rows.append([KeyboardButton(text=BTN_BACK)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Действия по матчу")


def matches_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_MATCHES), KeyboardButton(text=BTN_BROWSE)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def waiting_answer_keyboard() -> ReplyKeyboardMarkup:
    return game_waiting_answer_keyboard()


def waiting_partner_keyboard() -> ReplyKeyboardMarkup:
    return game_waiting_partner_keyboard()


def round_finished_keyboard() -> ReplyKeyboardMarkup:
    return game_round_finished_keyboard()


def contact_revealed_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_MATCH_SHOW_CONTACT), KeyboardButton(text=BTN_MATCH_REBROWSE)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Контакт раскрыт",
    )


def closed_match_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_MATCH_REBROWSE), KeyboardButton(text=BTN_MATCH_REMOVE)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Матч закрыт",
    )


def additional_game_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CHALLENGE), KeyboardButton(text=BTN_DICE)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Дополнительные активности",
    )


def settings_keyboard(city_filter_enabled: bool) -> ReplyKeyboardMarkup:
    city_label = f"{BTN_CITY_FILTER}: {'ВКЛ' if city_filter_enabled else 'ВЫКЛ'}"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=city_label)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Настройки",
    )


def profile_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_EDIT_PROFILE), KeyboardButton(text=BTN_DELETE_PROFILE_ELEMENT)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Анкета",
    )


def profile_edit_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_EDIT_NAME), KeyboardButton(text=BTN_EDIT_AGE)],
            [KeyboardButton(text=BTN_EDIT_CITY), KeyboardButton(text=BTN_EDIT_BIO)],
            [KeyboardButton(text=BTN_EDIT_PHOTO), KeyboardButton(text=BTN_EDIT_VOICE)],
            [KeyboardButton(text=BTN_EDIT_VIDEO_NOTE)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что изменить?",
    )


def profile_delete_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DELETE_BIO), KeyboardButton(text=BTN_DELETE_PHOTO)],
            [KeyboardButton(text=BTN_DELETE_VOICE), KeyboardButton(text=BTN_DELETE_VIDEO_NOTE)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Что удалить?",
    )


def unregistered_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_START_REG)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        input_field_placeholder="Сначала регистрация",
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)], [KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🙋‍♂️ Парень"), KeyboardButton(text="🙋‍♀️ Девушка")], [KeyboardButton(text="✨ Другое")]],
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


def game_invite_inline_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_game:{match_id}"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"decline_game:{match_id}"),
        ]]
    )


def match_select_inline_keyboard(matches: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{m['partner_name']} • {m['status_ru']}", callback_data=f"match:{m['id']}")] for m in matches[:20]]
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Пусто", callback_data="noop")]])


def reveal_contact_inline_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Да, раскрыть контакт", callback_data=f"accept_reveal:{match_id}"),
            InlineKeyboardButton(text="❌ Нет, продолжить игру", callback_data=f"decline_reveal:{match_id}"),
        ]]
    )


def choice_answer_inline_keyboard(match_id: int, options: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=o, callback_data=f"choice_answer:{match_id}:{idx}")] for idx, o in enumerate(options[:5])]
    return InlineKeyboardMarkup(inline_keyboard=rows)
