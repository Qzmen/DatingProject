from __future__ import annotations

import aiosqlite


class UserService:
    def __init__(self, db_path: str, default_stars_balance: int) -> None:
        self.db_path = db_path
        self.default_stars_balance = default_stars_balance

    async def get_by_tg_id(self, tg_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await db.execute_fetchone("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            return dict(row) if row else None

    async def create_or_update(self, tg_id: int, name: str, age: int, gender: str, city: str, photo_file_id: str | None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (tg_id, name, age, gender, city, photo_file_id, stars_balance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tg_id) DO UPDATE SET
                    name=excluded.name,
                    age=excluded.age,
                    gender=excluded.gender,
                    city=excluded.city,
                    photo_file_id=excluded.photo_file_id
                """,
                (tg_id, name, age, gender, city, photo_file_id, self.default_stars_balance),
            )
            await db.commit()

    async def list_users(self, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                "SELECT tg_id, name, age, gender, city, rating_score, rating_count, is_blocked FROM users ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in rows]

    async def block_user(self, tg_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("UPDATE users SET is_blocked = 1 WHERE tg_id = ?", (tg_id,))
            await db.commit()
            return cursor.rowcount > 0
