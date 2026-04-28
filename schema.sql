CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    city TEXT NOT NULL,
    city_normalized TEXT NOT NULL DEFAULT "",
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
    prefer_same_city INTEGER NOT NULL DEFAULT 1,
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
    expected_answer_type TEXT NOT NULL DEFAULT 'text',
    choice_options TEXT,
    round_started_at TEXT,
    round_expires_at TEXT,
    game_invited_by INTEGER,
    challenge_text TEXT,
    challenge_expires_at TEXT,
    challenge_user1_done INTEGER NOT NULL DEFAULT 0,
    challenge_user2_done INTEGER NOT NULL DEFAULT 0,
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
    delivered_to_partner INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_city_normalized ON users(city_normalized);

CREATE TABLE IF NOT EXISTS pair_cooldowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user1_id, user2_id)
);

CREATE INDEX IF NOT EXISTS idx_pair_cooldowns_expires_at ON pair_cooldowns(expires_at);

CREATE TABLE IF NOT EXISTS lobbies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    city_normalized TEXT NOT NULL,
    title TEXT NOT NULL,
    owner_user_id INTEGER NOT NULL,
    max_players INTEGER NOT NULL DEFAULT 6,
    visibility TEXT NOT NULL DEFAULT 'public',
    invite_code TEXT,
    status TEXT NOT NULL DEFAULT 'waiting',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS lobby_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lobby_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'active',
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at TEXT,
    last_seen_at TEXT,
    UNIQUE(lobby_id, user_id)
);

CREATE TABLE IF NOT EXISTS bottle_spins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lobby_id INTEGER NOT NULL,
    spinner_user_id INTEGER NOT NULL,
    selected_user_id INTEGER NOT NULL,
    angle REAL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bottle_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spin_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(spin_id, from_user_id, action)
);
