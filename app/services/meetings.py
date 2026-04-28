from __future__ import annotations

from datetime import UTC, datetime, timedelta
import aiosqlite


class MeetingService:
    def __init__(self, db_path: str, meeting_price_stars: int) -> None:
        self.db_path = db_path
        self.meeting_price_stars = meeting_price_stars

    async def get_match(self, match_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            return dict(row) if row else None

    async def users_for_match(self, match_id: int) -> tuple[dict, dict] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT user1_id, user2_id FROM matches WHERE id = ?", (match_id,))
            if not match:
                return None
            user1 = await self._fetchone(db, "SELECT * FROM users WHERE id = ?", (match["user1_id"],))
            user2 = await self._fetchone(db, "SELECT * FROM users WHERE id = ?", (match["user2_id"],))
            if not user1 or not user2:
                return None
            return dict(user1), dict(user2)

    async def confirm_meeting(self, match_id: int, user_id: int) -> tuple[bool, str]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match["status"] != "pending_confirm":
                return False, "Матч уже недоступен."

            if user_id not in (match["user1_id"], match["user2_id"]):
                return False, "Это не ваш матч."

            user = await self._fetchone(db, "SELECT * FROM users WHERE id = ?", (user_id,))
            if not user or user["stars_balance"] < self.meeting_price_stars:
                return False, "Недостаточно Telegram Stars (mock)."

            stars_column = "user1_stars_locked" if user_id == match["user1_id"] else "user2_stars_locked"
            confirmed_column = "user1_confirmed" if user_id == match["user1_id"] else "user2_confirmed"

            await db.execute("UPDATE users SET stars_balance = stars_balance - ? WHERE id = ?", (self.meeting_price_stars, user_id))
            await db.execute(
                f"UPDATE matches SET {confirmed_column} = 1, {stars_column} = ? WHERE id = ?",
                (self.meeting_price_stars, match_id),
            )

            refreshed = await self._fetchone(db, "SELECT user1_confirmed, user2_confirmed FROM matches WHERE id = ?", (match_id,))
            if refreshed and refreshed["user1_confirmed"] and refreshed["user2_confirmed"]:
                await db.execute("UPDATE matches SET status = 'confirmed' WHERE id = ?", (match_id,))
            await db.commit()
            return True, "Подтверждение принято."

    async def reject_meeting(self, match_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            match = await self._fetchone(db, "SELECT user1_id, user2_id FROM matches WHERE id = ?", (match_id,))
            if not match or user_id not in (match[0], match[1]):
                return False
            await db.execute("UPDATE matches SET status = 'cancelled' WHERE id = ?", (match_id,))
            await self._refund_locked(db, match_id)
            await db.commit()
            return True

    async def store_precheck(self, match_id: int, user_id: int, going: bool) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match["status"] != "confirmed":
                return False
            if user_id == match["user1_id"]:
                await db.execute("UPDATE matches SET user1_precheck = ? WHERE id = ?", (1 if going else 0, match_id))
            elif user_id == match["user2_id"]:
                await db.execute("UPDATE matches SET user2_precheck = ? WHERE id = ?", (1 if going else 0, match_id))
            else:
                return False

            if not going:
                await db.execute("UPDATE matches SET status = 'cancelled' WHERE id = ?", (match_id,))
                await self._refund_locked(db, match_id)
            await db.commit()
            return True

    async def save_feedback(self, match_id: int, from_user_id: int, came: bool) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match["status"] != "confirmed":
                return False

            if from_user_id == match["user1_id"]:
                target_id = match["user2_id"]
                await db.execute("UPDATE matches SET user1_feedback = ? WHERE id = ?", (1 if came else 0, match_id))
            elif from_user_id == match["user2_id"]:
                target_id = match["user1_id"]
                await db.execute("UPDATE matches SET user2_feedback = ? WHERE id = ?", (1 if came else 0, match_id))
            else:
                return False

            await db.execute(
                "INSERT OR REPLACE INTO feedback(match_id, from_user_id, target_user_id, came) VALUES (?, ?, ?, ?)",
                (match_id, from_user_id, target_id, 1 if came else 0),
            )

            updated = await self._fetchone(db, "SELECT user1_feedback, user2_feedback FROM matches WHERE id = ?", (match_id,))
            if updated and updated["user1_feedback"] is not None and updated["user2_feedback"] is not None:
                await db.execute("UPDATE matches SET status = 'completed' WHERE id = ?", (match_id,))
                await self._settle_stars_and_rating(db, match_id)

            await db.commit()
            return True

    async def pending_confirm_expired(self) -> list[int]:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM matches WHERE status IN ('pending_call','pending_confirm') AND confirm_deadline < ?", (now,)) as cursor:
                rows = await cursor.fetchall()
            ids = [row[0] for row in rows]
            for match_id in ids:
                await db.execute("UPDATE matches SET status='expired' WHERE id = ?", (match_id,))
                await self._refund_locked(db, match_id)
            await db.commit()
            return ids

    async def due_precheck(self) -> list[dict]:
        now = datetime.now(UTC)
        after = now + timedelta(hours=3)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM matches
                WHERE status='confirmed'
                  AND precheck_sent_at IS NULL
                  AND meetup_time <= ?
                """,
                (after.isoformat(),),
            ) as cursor:
                rows = await cursor.fetchall()
            ids = [row["id"] for row in rows]
            for match_id in ids:
                await db.execute("UPDATE matches SET precheck_sent_at = ? WHERE id = ?", (now.isoformat(), match_id))
            await db.commit()
            return [dict(r) for r in rows]

    async def cancel_precheck_timeouts(self) -> list[int]:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT id FROM matches
                WHERE status='confirmed'
                  AND meetup_time < ?
                  AND (user1_precheck IS NULL OR user2_precheck IS NULL)
                """,
                (now,),
            ) as cursor:
                rows = await cursor.fetchall()
            ids = [row[0] for row in rows]
            for match_id in ids:
                await db.execute("UPDATE matches SET status='cancelled' WHERE id = ?", (match_id,))
                await self._refund_locked(db, match_id)
            await db.commit()
            return ids

    async def due_feedback(self) -> list[dict]:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM matches
                WHERE status='confirmed'
                  AND meetup_time < ?
                  AND (user1_feedback IS NULL OR user2_feedback IS NULL)
                """,
                (now,),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def _refund_locked(self, db: aiosqlite.Connection, match_id: int) -> None:
        db.row_factory = aiosqlite.Row
        match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
        if not match:
            return
        if match["user1_stars_locked"] > 0:
            await db.execute("UPDATE users SET stars_balance = stars_balance + ? WHERE id = ?", (match["user1_stars_locked"], match["user1_id"]))
            await db.execute("UPDATE matches SET user1_stars_locked = 0 WHERE id = ?", (match_id,))
        if match["user2_stars_locked"] > 0:
            await db.execute("UPDATE users SET stars_balance = stars_balance + ? WHERE id = ?", (match["user2_stars_locked"], match["user2_id"]))
            await db.execute("UPDATE matches SET user2_stars_locked = 0 WHERE id = ?", (match_id,))

    async def _settle_stars_and_rating(self, db: aiosqlite.Connection, match_id: int) -> None:
        db.row_factory = aiosqlite.Row
        match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
        if not match:
            return

        for user_col, lock_col, feedback_col in (("user1_id", "user1_stars_locked", "user1_feedback"), ("user2_id", "user2_stars_locked", "user2_feedback")):
            user_id = match[user_col]
            locked = match[lock_col]
            came = match[feedback_col] == 1
            if came and locked > 0:
                await db.execute("UPDATE users SET stars_balance = stars_balance + ? WHERE id = ?", (locked, user_id))
            await db.execute(f"UPDATE matches SET {lock_col} = 0 WHERE id = ?", (match_id,))

        for target_col, source_col in (("user1_id", "user2_feedback"), ("user2_id", "user1_feedback")):
            target_user = match[target_col]
            came_vote = match[source_col]
            delta = 1 if came_vote == 1 else -1
            await db.execute(
                "UPDATE users SET rating_score = rating_score + ?, rating_count = rating_count + 1 WHERE id = ?",
                (delta, target_user),
            )

        await db.execute(
            "UPDATE users SET is_blocked = 1 WHERE rating_count >= 3 AND (CAST(rating_score AS REAL)/rating_count) <= -0.5"
        )



    async def mutual_matches_for_user(self, user_id: int, limit: int = 20) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT m.id, m.status,
                       CASE WHEN m.user1_id = ? THEN u2.name ELSE u1.name END AS partner_name,
                       CASE WHEN m.user1_id = ? THEN u2.tg_id ELSE u1.tg_id END AS partner_tg_id
                FROM matches m
                JOIN users u1 ON u1.id = m.user1_id
                JOIN users u2 ON u2.id = m.user2_id
                WHERE (m.user1_id = ? OR m.user2_id = ?)
                  AND m.status IN ('mutual_like','pending_call','call_cancelled','pending_confirm')
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (user_id, user_id, user_id, user_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def confirm_partner(self, match_id: int, user_id: int, approved: bool) -> tuple[bool, str, dict | None]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match['status'] != 'pending_confirm':
                return False, 'Пара недоступна для подтверждения.', None
            if user_id not in (match['user1_id'], match['user2_id']):
                return False, 'Это не ваша пара.', None

            if not approved:
                await db.execute("UPDATE matches SET status = 'call_cancelled' WHERE id = ?", (match_id,))
                await db.execute("DELETE FROM likes WHERE (liker_id = ? AND liked_id = ?) OR (liker_id = ? AND liked_id = ?)", (match['user1_id'], match['user2_id'], match['user2_id'], match['user1_id']))
                await db.commit()
                return True, 'Понял, идём дальше 👌', None

            col = 'user1_confirmed' if user_id == match['user1_id'] else 'user2_confirmed'
            await db.execute(f"UPDATE matches SET {col}=1 WHERE id = ?", (match_id,))
            updated = await self._fetchone(db, "SELECT user1_confirmed, user2_confirmed FROM matches WHERE id = ?", (match_id,))
            if updated and updated['user1_confirmed'] and updated['user2_confirmed']:
                await db.execute("UPDATE matches SET status = 'partner_shared' WHERE id = ?", (match_id,))
                partner_id = match['user2_id'] if user_id == match['user1_id'] else match['user1_id']
                partner = await self._fetchone(db, "SELECT tg_id, name FROM users WHERE id = ?", (partner_id,))
                await db.commit()
                return True, 'Оба подтвердили партнёра!', dict(partner) if partner else None

            await db.commit()
            return True, 'Отлично, ждём решение второго человека.', None

    async def pending_call_match_for_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(
                db,
                """
                SELECT * FROM matches
                WHERE status = 'pending_call'
                  AND (user1_id = ? OR user2_id = ?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, user_id),
            )
            return dict(row) if row else None

    async def request_call(self, match_id: int, user_id: int) -> tuple[bool, str]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match["status"] not in ("mutual_like", "pending_call", "call_cancelled"):
                return False, "Матч для звонка недоступен."
            if user_id not in (match["user1_id"], match["user2_id"]):
                return False, "Это не ваш матч."

            accept_col = "user1_call_accepted" if user_id == match["user1_id"] else "user2_call_accepted"
            await db.execute(
                "UPDATE matches SET status = 'pending_call', call_requested_by = ?, user1_call_accepted = 0, user2_call_accepted = 0 WHERE id = ?",
                (user_id, match_id),
            )
            await db.execute(f"UPDATE matches SET {accept_col} = 1 WHERE id = ?", (match_id,))
            await db.commit()
            return True, "Запрос на звонок отправлен."

    async def respond_call(self, match_id: int, user_id: int, accepted: bool) -> tuple[bool, str]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            match = await self._fetchone(db, "SELECT * FROM matches WHERE id = ?", (match_id,))
            if not match or match["status"] not in ("mutual_like", "pending_call", "call_cancelled"):
                return False, "Матч для звонка недоступен."
            if user_id not in (match["user1_id"], match["user2_id"]):
                return False, "Это не ваш матч."
            if match["call_requested_by"] is None:
                return False, "Сначала кто-то должен отправить запрос на звонок."

            if not accepted:
                await db.execute("UPDATE matches SET status = 'call_cancelled' WHERE id = ?", (match_id,))
                await db.execute("DELETE FROM likes WHERE (liker_id = ? AND liked_id = ?) OR (liker_id = ? AND liked_id = ?)", (match['user1_id'], match['user2_id'], match['user2_id'], match['user1_id']))
                await db.commit()
                return True, "Звонок отклонён. Можно лайкнуть друг друга снова."

            if user_id == match["user1_id"]:
                await db.execute("UPDATE matches SET user1_call_accepted = 1 WHERE id = ?", (match_id,))
            else:
                await db.execute("UPDATE matches SET user2_call_accepted = 1 WHERE id = ?", (match_id,))

            refreshed = await self._fetchone(
                db,
                "SELECT user1_call_accepted, user2_call_accepted FROM matches WHERE id = ?",
                (match_id,),
            )
            if refreshed and refreshed["user1_call_accepted"] and refreshed["user2_call_accepted"]:
                confirm_deadline = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
                call_room_url = self._build_call_link(match_id)
                await db.execute(
                    "UPDATE matches SET status = 'pending_confirm', confirm_deadline = ?, call_room_url = ? WHERE id = ?",
                    (confirm_deadline, call_room_url, match_id),
                )
                await db.commit()
                return True, "Звонок согласован. Ссылка на конференцию создана."

            await db.commit()
            return True, "Ожидаем подтверждение звонка от второго участника."

    async def pending_match_for_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(
                db,
                """
                SELECT * FROM matches
                WHERE status = 'pending_confirm'
                  AND (user1_id = ? OR user2_id = ?)
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, user_id),
            )
            return dict(row) if row else None

    async def precheck_match_for_user(self, user_id: int) -> dict | None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(
                db,
                """
                SELECT * FROM matches
                WHERE status = 'confirmed'
                  AND precheck_sent_at IS NOT NULL
                  AND meetup_time > ?
                  AND (user1_id = ? OR user2_id = ?)
                  AND (
                    (user1_id = ? AND user1_precheck IS NULL)
                    OR (user2_id = ? AND user2_precheck IS NULL)
                  )
                ORDER BY id DESC
                LIMIT 1
                """,
                (now, user_id, user_id, user_id, user_id),
            )
            return dict(row) if row else None

    async def feedback_match_for_user(self, user_id: int) -> dict | None:
        now = datetime.now(UTC).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(
                db,
                """
                SELECT * FROM matches
                WHERE status = 'confirmed'
                  AND meetup_time < ?
                  AND (user1_id = ? OR user2_id = ?)
                  AND (
                    (user1_id = ? AND user1_feedback IS NULL)
                    OR (user2_id = ? AND user2_feedback IS NULL)
                  )
                ORDER BY id DESC
                LIMIT 1
                """,
                (now, user_id, user_id, user_id, user_id),
            )
            return dict(row) if row else None

    def _build_call_link(self, match_id: int) -> str:
        # Обычная открытая комната без обязательного модератора/токенов
        return f"https://meet.jit.si/dating-room-{match_id}"

    async def _fetchone(self, db: aiosqlite.Connection, query: str, params: tuple) -> aiosqlite.Row | None:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchone()
