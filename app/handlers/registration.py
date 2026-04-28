import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import (
    BTN_PROFILE,
    BTN_SKIP,
    gender_keyboard,
    main_menu_keyboard,
    skip_keyboard,
)
from app.states import RegistrationStates

router = Router()


@router.message(Command("start"))
async def start_registration(message: Message, state: FSMContext) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if me:
        await message.answer("Главное меню 💫", reply_markup=main_menu_keyboard())
        return
    await state.set_state(RegistrationStates.waiting_name)
    await message.answer("Привет! Давай создадим красивую анкету.\n\nКак тебя зовут?")


@router.message(RegistrationStates.waiting_name)
async def save_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\-\s]{2,30}", name):
        await message.answer("Имя должно быть 2-30 символов и состоять из букв.")
        return
    await state.update_data(name=name)
    await state.set_state(RegistrationStates.waiting_age)
    await message.answer("Сколько тебе лет?")


@router.message(RegistrationStates.waiting_age)
async def save_age(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    if not txt.isdigit() or int(txt) < 18 or int(txt) > 40:
        await message.answer("Возраст должен быть не меньше 18 лет.")
        return
    await state.update_data(age=int(txt))
    await state.set_state(RegistrationStates.waiting_gender)
    await message.answer("Укажи пол", reply_markup=gender_keyboard())


@router.message(RegistrationStates.waiting_gender)
async def save_gender(message: Message, state: FSMContext) -> None:
    raw_gender = (message.text or "").strip()
    gender_map = {"🙋‍♂️ Парень": "Парень", "🙋‍♀️ Девушка": "Девушка", "✨ Другое": "Другое"}
    await state.update_data(gender=gender_map.get(raw_gender, raw_gender or "Не указан"))
    await state.set_state(RegistrationStates.waiting_city)
    await message.answer("Из какого ты города?")


@router.message(RegistrationStates.waiting_city)
async def save_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if len(city) < 2:
        await message.answer("Укажи город корректно.")
        return
    await state.update_data(city=city)
    await state.set_state(RegistrationStates.waiting_bio)
    await message.answer("Расскажи немного о себе. (до 500 символов)")


@router.message(RegistrationStates.waiting_bio)
async def save_bio(message: Message, state: FSMContext) -> None:
    bio = (message.text or "").strip()
    if not bio or len(bio) > 500:
        await message.answer("Описание должно быть от 1 до 500 символов.")
        return
    await state.update_data(description=bio)
    await state.set_state(RegistrationStates.waiting_photo)
    await message.answer("Отправь фото профиля или нажми «Пропустить».", reply_markup=skip_keyboard())


@router.message(RegistrationStates.waiting_photo, Command("skip_photo"))
@router.message(RegistrationStates.waiting_photo, F.text == BTN_SKIP)
async def skip_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=None)
    await state.set_state(RegistrationStates.waiting_voice)
    await message.answer("Запиши голосовое приветствие (до 30 сек) или нажми «Пропустить».", reply_markup=skip_keyboard())


@router.message(RegistrationStates.waiting_photo, F.photo)
async def save_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(RegistrationStates.waiting_voice)
    await message.answer("Отлично! Теперь голосовое приветствие (до 30 сек) или «Пропустить».", reply_markup=skip_keyboard())


@router.message(RegistrationStates.waiting_photo)
async def only_photo(message: Message) -> None:
    await message.answer("Отправь фото или нажми «Пропустить».")


@router.message(RegistrationStates.waiting_voice, Command("skip_voice"))
@router.message(RegistrationStates.waiting_voice, F.text == BTN_SKIP)
async def skip_voice(message: Message, state: FSMContext) -> None:
    await state.update_data(voice_file_id=None)
    await state.set_state(RegistrationStates.waiting_video_note)
    await message.answer("Отправь кружок Telegram или нажми «Пропустить».", reply_markup=skip_keyboard())


@router.message(RegistrationStates.waiting_voice, F.voice)
async def save_voice(message: Message, state: FSMContext) -> None:
    if message.voice and message.voice.duration and message.voice.duration > 30:
        await message.answer("Голосовое должно быть до 30 секунд.")
        return
    await state.update_data(voice_file_id=message.voice.file_id)
    await state.set_state(RegistrationStates.waiting_video_note)
    await message.answer("Супер! Остался кружок Telegram или «Пропустить».", reply_markup=skip_keyboard())


@router.message(RegistrationStates.waiting_voice)
async def only_voice(message: Message) -> None:
    await message.answer("Отправь голосовое или нажми «Пропустить».")


@router.message(RegistrationStates.waiting_video_note, Command("skip_video_note"))
@router.message(RegistrationStates.waiting_video_note, F.text == BTN_SKIP)
async def finish_skip_video(message: Message, state: FSMContext) -> None:
    await _finish(message, state, None)


@router.message(RegistrationStates.waiting_video_note, F.video_note)
async def save_video_note(message: Message, state: FSMContext) -> None:
    await _finish(message, state, message.video_note.file_id)


@router.message(RegistrationStates.waiting_video_note, F.video)
async def reject_regular_video(message: Message) -> None:
    await message.answer("Нужен именно кружок Telegram. Или нажми «Пропустить».")


@router.message(RegistrationStates.waiting_video_note)
async def only_video_note(message: Message) -> None:
    await message.answer("Отправь кружок Telegram или нажми «Пропустить».")


@router.message(Command("profile"))
@router.message(F.text == BTN_PROFILE)
async def profile(message: Message) -> None:
    me = await message.bot.user_service.get_by_tg_id(message.from_user.id)
    if not me:
        await message.answer("Сначала /start")
        return
    text = f"{me['name']} {me['age']} ({me['city']})\n{me.get('description') or ''}\n⭐ Репутация: {me.get('reputation_score', 0)}"
    if me.get("photo_file_id"):
        await message.answer_photo(me["photo_file_id"], caption=text)
    else:
        await message.answer(text)


async def _finish(message: Message, state: FSMContext, video_note_file_id: str | None) -> None:
    data = await state.get_data()
    await message.bot.user_service.create_or_update(
        tg_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        city=data["city"],
        description=data["description"],
        photo_file_id=data.get("photo_file_id"),
        voice_file_id=data.get("voice_file_id"),
        video_note_file_id=video_note_file_id,
    )
    await state.clear()
    await message.answer(
        "✅ Регистрация завершена! Всё готово для знакомств.",
        reply_markup=main_menu_keyboard(),
    )
