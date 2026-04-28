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
    REG_SKIP_PHOTO,
    main_menu_keyboard,
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
    await message.answer(
        "✨ Привет! Давай сделаем твою анкету.\n\n"
        "Напиши имя (только буквы, 2-30 символов)."
    )


@router.message(RegistrationStates.waiting_name)
async def save_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\-\s]{2,30}", text):
        await message.answer("Имя должно быть 2-30 символов и состоять только из букв.")
        return

    await state.update_data(name=" ".join(text.split()))
    await state.set_state(RegistrationStates.waiting_age)
    await message.answer("Сколько тебе лет? Введи только число от 18 до 99.")


@router.message(RegistrationStates.waiting_age)
async def save_age(message: Message, state: FSMContext) -> None:
    age_text = (message.text or "").strip()
    if not age_text.isdigit():
        await message.answer("Возраст можно вводить только цифрами.")
        return

    age = int(age_text)
    if not 18 <= age <= 99:
        await message.answer("Возраст должен быть от 18 до 99.")
        return

    await state.update_data(age=age)
    await state.set_state(RegistrationStates.waiting_gender)
    await message.answer(
        "Выбери пол кнопкой ниже 👇",
        reply_markup=registration_gender_keyboard(),
    )


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
    await state.set_state(RegistrationStates.waiting_photo)
    await message.answer(
        "Отправь фото профиля или нажми кнопку «Пропустить фото».",
        reply_markup=registration_photo_keyboard(),
    )


@router.message(RegistrationStates.waiting_photo, F.text == REG_SKIP_PHOTO)
async def finish_without_photo(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, None)


@router.message(RegistrationStates.waiting_photo, F.photo)
async def finish_with_photo(message: Message, state: FSMContext) -> None:
    photo_id = message.photo[-1].file_id
    await _finish_registration(message, state, photo_id)


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
    text = (
        "👤 Твоя анкета\n"
        f"Имя: {me['name']}\n"
        f"Возраст: {me['age']}\n"
        f"Пол: {me['gender']}\n"
        f"Город: {me['city']}\n"
        f"Баланс Stars: {me['stars_balance']}\n"
        f"Статус: {status}"
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
    user_service = message.bot.user_service
    data = await state.get_data()
    await user_service.create_or_update(
        tg_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        city=data["city"],
        photo_file_id=photo_file_id,
    )
    await state.clear()
    await message.answer(
        "🎉 Регистрация завершена!"
        "\nТеперь пользуйся нижним меню: там поиск анкет и управление профилем.",
        reply_markup=main_menu_keyboard(profile_enabled=True),
    )
