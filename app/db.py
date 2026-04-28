import aiosqlite

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    city TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT "",
    description TEXT NOT NULL DEFAULT "",
    photo_file_id TEXT,
    voice_file_id TEXT,
    video_note_file_id TEXT,
    stars_balance INTEGER NOT NULL DEFAULT 100,
    rating_score INTEGER NOT NULL DEFAULT 0,
    reputation_score INTEGER NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    is_blocked INTEGER NOT NULL DEFAULT 0,
    is_profile_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    liker_id INTEGER NOT NULL,
    liked_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(liker_id, liked_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    game_round INTEGER NOT NULL DEFAULT 0,
    game_prompt TEXT,
    game_invited_by INTEGER,
    user1_reveal_requested INTEGER NOT NULL DEFAULT 0,
    user2_reveal_requested INTEGER NOT NULL DEFAULT 0,
    contact_revealed_at TEXT
);

CREATE TABLE IF NOT EXISTS match_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    sender_user_id INTEGER NOT NULL,
    message_type TEXT NOT NULL,
    text TEXT,
    file_id TEXT,
    prompt TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db(database_url: str) -> None:
    async with aiosqlite.connect(database_url) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
