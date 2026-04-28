import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import (
    MAIN_MENU_DISABLE,
    MAIN_MENU_ENABLE,
    MAIN_MENU_PROFILE,
    REG_GENDER_FEMALE,
    REG_GENDER_MALE,
    REG_GENDER_OTHER,
    REG_SKIP_BIO,
    REG_SKIP_PHOTO,
    main_menu_keyboard,
    registration_bio_keyboard,
    registration_gender_keyboard,
    registration_photo_keyboard,
)
from app.states import RegistrationStates

router = Router()

_ALLOWED_GENDERS = {
    REG_GENDER_MALE: "Мужчина",
    REG_GENDER_FEMALE: "Женщина",
    REG_GENDER_OTHER: "Другое",
}


@router.message(Command("start"))
async def start_registration(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_name)
    await message.answer("✨ Привет! Давай сделаем твою анкету.\n\nНапиши имя (только буквы, 2-30 символов).")


@router.message(RegistrationStates.waiting_name)
async def save_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\-\s]{2,30}", text):
        await message.answer("Имя должно быть 2-30 символов и состоять только из букв.")
        return

    await state.update_data(name=" ".join(text.split()))
    await state.set_state(RegistrationStates.waiting_age)
    await message.answer("Сколько тебе лет? Введи только число.")


@router.message(RegistrationStates.waiting_age)
async def save_age(message: Message, state: FSMContext) -> None:
    age_text = (message.text or "").strip()
    if not age_text.isdigit():
        await message.answer("Возраст можно вводить только цифрами.")
        return

    age = int(age_text)
    if age < 18 or age > 40:
        await message.answer("Введите корректный возраст (18+).")
        return

    await state.update_data(age=age)
    await state.set_state(RegistrationStates.waiting_gender)
    await message.answer("Выбери пол кнопкой ниже 👇", reply_markup=registration_gender_keyboard())


@router.message(RegistrationStates.waiting_gender)
async def save_gender(message: Message, state: FSMContext) -> None:
    gender_text = (message.text or "").strip()
    if gender_text not in _ALLOWED_GENDERS:
        await message.answer("Нажми одну из кнопок выбора пола 👇", reply_markup=registration_gender_keyboard())
        return

    await state.update_data(gender=_ALLOWED_GENDERS[gender_text])
    await state.set_state(RegistrationStates.waiting_city)
    await message.answer("Из какого ты города? Только буквы, до 50 символов.")


@router.message(RegistrationStates.waiting_city)
async def save_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\-\s]{2,50}", city):
        await message.answer("Город должен содержать только буквы (2-50 символов).")
        return

    await state.update_data(city=" ".join(city.split()))
    await state.set_state(RegistrationStates.waiting_bio)
    await message.answer(
        "Напиши короткое описание о себе (до 240 символов) или пропусти.",
        reply_markup=registration_bio_keyboard(),
    )


@router.message(RegistrationStates.waiting_bio, F.text == REG_SKIP_BIO)
async def skip_bio(message: Message, state: FSMContext) -> None:
    await state.update_data(bio="")
    await state.set_state(RegistrationStates.waiting_photo)
    await message.answer("Отправь фото профиля или нажми кнопку «Пропустить фото».", reply_markup=registration_photo_keyboard())


@router.message(RegistrationStates.waiting_bio)
async def save_bio(message: Message, state: FSMContext) -> None:
    bio = (message.text or "").strip()
    if not bio:
        await message.answer("Описание не должно быть пустым. Напиши пару слов или нажми «Пропустить описание».", reply_markup=registration_bio_keyboard())
        return
    if len(bio) > 240:
        await message.answer("Описание слишком длинное. Сделай до 240 символов.")
        return

    await state.update_data(bio=bio)
    await state.set_state(RegistrationStates.waiting_photo)
    await message.answer("Отправь фото профиля или нажми кнопку «Пропустить фото».", reply_markup=registration_photo_keyboard())


@router.message(RegistrationStates.waiting_photo, F.text == REG_SKIP_PHOTO)
async def finish_without_photo(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, None)


@router.message(RegistrationStates.waiting_photo, F.photo)
async def finish_with_photo(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, message.photo[-1].file_id)


@router.message(RegistrationStates.waiting_photo)
async def wait_for_photo(message: Message) -> None:
    await message.answer("Нужна фотография или кнопка «Пропустить фото».", reply_markup=registration_photo_keyboard())


@router.message(F.text == MAIN_MENU_PROFILE)
async def show_profile(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала заполни анкету через /start")
        return

    status = "✅ включена" if me["is_blocked"] == 0 else "⏸ отключена"
    bio = me.get("bio") or "—"
    reputation = _format_reputation(me["rating_score"], me["rating_count"])
    text = (
        f"👤 {me['name']}, {me['age']} ({me['city']})\n"
        f"{bio}\n"
        f"⭐ {me['stars_balance']} | Репутация: {reputation}\n"
        f"Статус анкеты: {status}"
    )
    await message.answer(text, reply_markup=main_menu_keyboard(profile_enabled=me["is_blocked"] == 0))


@router.message(F.text == MAIN_MENU_DISABLE)
async def disable_profile(message: Message) -> None:
    updated = await message.bot.user_service.set_profile_enabled(message.from_user.id, enabled=False)
    if not updated:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    await message.answer("Анкета отключена. Ты не будешь показываться в поиске.", reply_markup=main_menu_keyboard(profile_enabled=False))


@router.message(F.text == MAIN_MENU_ENABLE)
async def enable_profile(message: Message) -> None:
    updated = await message.bot.user_service.set_profile_enabled(message.from_user.id, enabled=True)
    if not updated:
        await message.answer("Сначала зарегистрируйся через /start")
        return
    await message.answer("Анкета снова активна ✅", reply_markup=main_menu_keyboard(profile_enabled=True))


async def _finish_registration(message: Message, state: FSMContext, photo_file_id: str | None) -> None:
    data = await state.get_data()
    await message.bot.user_service.create_or_update(
        tg_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        city=data["city"],
        bio=data.get("bio", ""),
        photo_file_id=photo_file_id,
    )
    await state.clear()
    await message.answer(
        "🎉 Регистрация завершена!\nТеперь пользуйся нижним меню.",
        reply_markup=main_menu_keyboard(profile_enabled=True),
    )


def _format_reputation(score: int, count: int) -> str:
    if count == 0:
        return "новичок"
    return f"{score / count:+.2f} ({count})"
