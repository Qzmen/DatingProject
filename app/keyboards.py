from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Кнопки для лайка/пропуска анкет
def browse_keyboard(candidate_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like:{candidate_id}"),
        InlineKeyboardButton(text="➡️ Пропустить", callback_data=f"skip:{candidate_id}")
    )
    return builder.as_markup()

# Кнопки для решения по встрече (подтвердить/отклонить)
def meeting_decision_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить встречу", callback_data=f"confirm_meeting:{match_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_meeting:{match_id}")
            ]
        ]
    )

# Кнопки precheck "Иду / Не иду"
def precheck_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Да, иду", callback_data=f"precheck_yes:{match_id}"),
                InlineKeyboardButton(text="👎 Нет", callback_data=f"precheck_no:{match_id}")
            ]
        ]
    )

# Кнопки посещения встречи
def attendance_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Да", callback_data=f"came_yes:{match_id}"),
                InlineKeyboardButton(text="👎 Нет", callback_data=f"came_no:{match_id}")
            ]
        ]
    )