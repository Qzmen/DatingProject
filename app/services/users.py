from __future__ import annotations

import aiosqlite


class UserService:
    def __init__(self, db_path: str, default_stars_balance: int) -> None:
        self.db_path = db_path
        self.default_stars_balance = default_stars_balance

    async def get_by_tg_id(self, tg_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_or_update(self, tg_id: int, name: str, age: int, gender: str, city: str, description: str, photo_file_id: str | None, voice_file_id: str | None, video_note_file_id: str | None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, name, age, gender, city, bio, description, photo_file_id, voice_file_id, video_note_file_id, stars_balance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tg_id) DO UPDATE SET
                    name=excluded.name,
                    age=excluded.age,
                    gender=excluded.gender,
                    city=excluded.city,
                    bio=excluded.bio,
                    description=excluded.description,
                    photo_file_id=excluded.photo_file_id,
                    voice_file_id=excluded.voice_file_id,
                    video_note_file_id=excluded.video_note_file_id
                """,
                (tg_id, name, age, gender, city, description, description, photo_file_id, voice_file_id, video_note_file_id, self.default_stars_balance),
            )
            await db.commit()

    async def list_users(self, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT tg_id, name, age, city, reputation_score, is_blocked, is_profile_enabled FROM users ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def block_user(self, tg_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("UPDATE users SET is_blocked = 1 WHERE tg_id = ?", (tg_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def set_profile_enabled(self, tg_id: int, enabled: bool) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("UPDATE users SET is_profile_enabled = ? WHERE tg_id = ?", (1 if enabled else 0, tg_id))
            await db.commit()
            return cursor.rowcount > 0
