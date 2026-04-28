from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.states import RegistrationStates

router = Router()


@router.message(Command("start"))
async def start_registration(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.waiting_name)
    await message.answer("Привет! Давай зарегистрируемся. Как тебя зовут?")


@router.message(RegistrationStates.waiting_name)
async def save_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_age)
    await message.answer("Сколько тебе лет?")


@router.message(RegistrationStates.waiting_age)
async def save_age(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit() or not (18 <= int(message.text) <= 99):
        await message.answer("Введи возраст числом от 18 до 99.")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(RegistrationStates.waiting_gender)
    await message.answer("Укажи пол (например: Мужчина / Женщина / Другое).")


@router.message(RegistrationStates.waiting_gender)
async def save_gender(message: Message, state: FSMContext) -> None:
    await state.update_data(gender=message.text.strip())
    await state.set_state(RegistrationStates.waiting_city)
    await message.answer("Из какого ты города?")


@router.message(RegistrationStates.waiting_city)
async def save_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text.strip())
    await state.set_state(RegistrationStates.waiting_photo)
    await message.answer("Отправь фото (опционально) или напиши /skip_photo")


@router.message(Command("skip_photo"), RegistrationStates.waiting_photo)
async def finish_without_photo(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, None)


@router.message(RegistrationStates.waiting_photo, F.photo)
async def finish_with_photo(message: Message, state: FSMContext) -> None:
    photo_id = message.photo[-1].file_id
    await _finish_registration(message, state, photo_id)


@router.message(RegistrationStates.waiting_photo)
async def wait_for_photo(message: Message) -> None:
    await message.answer("Отправь фото или команду /skip_photo")


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
    await message.answer("✅ Регистрация завершена! Используй /browse для поиска мэтча.")
