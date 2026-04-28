# Dating MVP Telegram Bot (aiogram)

MVP-бот для дейтинг-сервиса с ключевой механикой: **матч существует только при подтверждённой офлайн-встрече в ограниченное время**.

## Что реализовано

- Регистрация: имя, возраст, пол, город, фото (опционально).
- Просмотр случайных анкет в своём городе.
- Лайк / Пропустить.
- Взаимный лайк => матч.
- После взаимного лайка: этап запроса на совместный звонок.
- После согласованного звонка: подтверждение партнёра (да/нет). Если оба согласны — бот выдаёт Telegram ID партнёра.
- 24 часа на подтверждение (иначе матч удаляется).
- Double-check за 2–3 часа до встречи.
- Рейтинг надёжности по post-meeting feedback (`пришёл/не пришёл`).
- Ограничение: у пользователя только 1 активная встреча.
- Mock-монетизация Telegram Stars:
  - При подтверждении встречи списывается `MEETING_PRICE_STARS`.
  - Если пришёл — депозит возвращается.
  - Если не пришёл — депозит сгорает.
- Уведомления о ключевых событиях.
- Простая админка:
  - `/admin_users`
  - `/admin_matches`
  - `/block <tg_id>`

## Технологии

- Python 3.11+
- aiogram v3
- SQLite (через `aiosqlite`)
- Async/FSM

## Запуск

1. Установи зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создай `.env`:

```bash
cp .env.example .env
```

3. Укажи `BOT_TOKEN` и (опционально) `ADMIN_IDS`.

4. Запусти:

```bash
python main.py
```

## Команды пользователя

- `/start` — регистрация (остальное управление через кнопки в нижнем меню)
- Кнопки меню: «Смотреть анкеты», «Моя анкета», «Отключить/Включить анкету»

## Команды админа

- `/admin_users` — список пользователей
- `/admin_matches` — список матчей
- `/block <tg_id>` — блокировка пользователя

## Структура проекта

```text
app/
  handlers/
    registration.py
    browsing.py
    meetings.py
    admin.py
  services/
    users.py
    matching.py
    meetings.py
  bot.py
  config.py
  db.py
  keyboards.py
  logging_config.py
  scheduler.py
  states.py
main.py
schema.sql
.env.example
requirements.txt
```

## Схема БД

Полная SQL-схема: [`schema.sql`](./schema.sql)

Ключевые таблицы:
- `users`
- `likes`
- `matches`
- `feedback`

## Важные детали MVP

- Real payment API Telegram Stars заменён mock-логикой с `stars_balance`.
- Планировщик (`scheduler.py`) запускается циклом и проверяет:
  - истечение 24 часов на подтверждение,
  - pre-check перед встречей,
  - отмену при отсутствии pre-check,
  - отправку post-meeting feedback.

## Что можно улучшить в проде

- Перейти на PostgreSQL + SQLAlchemy/Alembic.
- Добавить транзакционные блокировки для гонок.
- Вынести scheduler в отдельный worker (APScheduler/Celery).
- Реальная интеграция Telegram Stars/payments.
- Более умный anti-fraud и reputation scoring.
