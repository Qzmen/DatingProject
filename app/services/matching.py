from __future__ import annotations

import aiosqlite
from datetime import datetime, timedelta, UTC


ACTIVE_STATUSES = ("pending_call", "pending_confirm")


class MatchingService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def has_active_meeting(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT id FROM matches
                WHERE (user1_id = ? OR user2_id = ?)
                  AND status IN ('pending_call', 'pending_confirm', 'confirmed')
                LIMIT 1
                """,
                (user_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
            return row is not None


    async def active_match_for_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, status FROM matches
                WHERE (user1_id = ? OR user2_id = ?)
                  AND status IN ('pending_call', 'pending_confirm', 'confirmed')
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def next_candidate(self, user_id: int, city: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT u.id, u.tg_id, u.name, u.age, u.gender, u.city, u.bio, u.photo_file_id, u.stars_balance, u.rating_score, u.rating_count
                FROM users u
                WHERE u.id != ?
                  AND u.city = ?
                  AND u.is_blocked = 0
                  AND u.is_profile_enabled = 1
                  AND u.id NOT IN (SELECT liked_id FROM likes WHERE liker_id = ?)
                  AND u.id NOT IN (
                    SELECT CASE WHEN m.user1_id = ? THEN m.user2_id ELSE m.user1_id END
                    FROM matches m
                    WHERE (m.user1_id = ? OR m.user2_id = ?)
                      AND m.status IN ('pending_call', 'pending_confirm', 'confirmed')
                  )
                ORDER BY RANDOM()
                LIMIT 1
                """,
                (user_id, city, user_id, user_id, user_id, user_id),
            ) as cursor:
                row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_like_and_try_match(self, liker_id: int, liked_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO likes(liker_id, liked_id) VALUES (?, ?)",
                (liker_id, liked_id),
            )

            async with db.execute(
                "SELECT id FROM likes WHERE liker_id = ? AND liked_id = ?",
                (liked_id, liker_id),
            ) as cursor:
                reciprocal = await cursor.fetchone()

            if not reciprocal:
                await db.commit()
                return None

            now = datetime.now(UTC)
            confirm_deadline = now + timedelta(hours=24)
            meetup_time = now + timedelta(hours=6)
            meetup_place = "Кофейня в центре"

            async with db.execute(
                """
                INSERT INTO matches(user1_id, user2_id, status, confirm_deadline, meetup_time, meetup_place)
                VALUES (?, ?, 'mutual_like', ?, ?, ?)
                """,
                (liker_id, liked_id, confirm_deadline.isoformat(), meetup_time.isoformat(), meetup_place),
            ) as cursor:
                match_id = cursor.lastrowid

            await db.commit()
            return {
                "id": match_id,
                "user1_id": liker_id,
                "user2_id": liked_id,
                "confirm_deadline": confirm_deadline.isoformat(),
                "meetup_time": meetup_time.isoformat(),
                "meetup_place": meetup_place,
            }


    async def list_matches(self, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, user1_id, user2_id, status, meetup_time, meetup_place "
                "FROM matches ORDER BY id DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def incoming_likes(self, user_id: int, limit: int = 20) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT u.id, u.name, u.age, u.city, u.bio, u.rating_score, u.rating_count, l.created_at
                FROM likes l
                JOIN users u ON u.id = l.liker_id
                WHERE l.liked_id = ?
                  AND l.liker_id NOT IN (SELECT liked_id FROM likes WHERE liker_id = ?)
                ORDER BY l.id DESC
                LIMIT ?
                """,
                (user_id, user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(row) for row in rows]
