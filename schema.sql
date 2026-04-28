CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    city TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT "",
    photo_file_id TEXT,
    stars_balance INTEGER NOT NULL DEFAULT 100,
    rating_score INTEGER NOT NULL DEFAULT 0,
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
    confirm_deadline TEXT NOT NULL,
    meetup_time TEXT NOT NULL,
    meetup_place TEXT NOT NULL,
    user1_confirmed INTEGER NOT NULL DEFAULT 0,
    user2_confirmed INTEGER NOT NULL DEFAULT 0,
    user1_stars_locked INTEGER NOT NULL DEFAULT 0,
    user2_stars_locked INTEGER NOT NULL DEFAULT 0,
    precheck_sent_at TEXT,
    user1_precheck INTEGER,
    user2_precheck INTEGER,
    user1_feedback INTEGER,
    user2_feedback INTEGER,
    call_requested_by INTEGER,
    user1_call_accepted INTEGER NOT NULL DEFAULT 0,
    user2_call_accepted INTEGER NOT NULL DEFAULT 0,
    call_room_url TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    from_user_id INTEGER NOT NULL,
    target_user_id INTEGER NOT NULL,
    came INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, from_user_id)
);
