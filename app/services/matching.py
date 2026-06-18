from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite

TEXT_PROMPTS = [
    "Выбери: прогулка ночью или кофе утром?",
    "Какой факт о тебе обычно удивляет людей?",
    "Опиши свой сегодняшний вайб тремя словами.",
]
VOICE_PROMPTS = [
    "Отправь голосовое до 20 секунд: какой у тебя сегодня настрой?",
    "Скажи голосом фразу, которая тебя лучше всего описывает.",
]
VIDEO_PROMPTS = [
    "Запиши кружок с коротким приветствием.",
    "Запиши кружок: один жест или эмоция, которая описывает твой день.",
]


class MatchingService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def get_user_by_tg(self, tg_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

    async def next_candidate(self, user_id: int, city: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, tg_id, name, age, city, description, photo_file_id, voice_file_id, video_note_file_id, reputation_score
                FROM users
                WHERE id != ? AND city = ? AND is_blocked = 0 AND is_profile_enabled = 1
                  AND id NOT IN (SELECT liked_id FROM likes WHERE liker_id = ?)
                ORDER BY RANDOM() LIMIT 1
                """,
                (user_id, city, user_id),
            ) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

    async def like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None]:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO likes(liker_id, liked_id) VALUES (?, ?)", (liker_id, liked_id))
            async with db.execute("SELECT 1 FROM likes WHERE liker_id=? AND liked_id=?", (liked_id, liker_id)) as cur:
                reciprocal = await cur.fetchone()
            if not reciprocal:
                await db.commit()
                return False, None

            async with db.execute(
                "SELECT id FROM matches WHERE ((user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?)) AND status!='closed' ORDER BY id DESC LIMIT 1",
                (liker_id, liked_id, liked_id, liker_id),
            ) as cur:
                existing = await cur.fetchone()
            if existing:
                await db.execute("UPDATE matches SET status='matched', updated_at=CURRENT_TIMESTAMP WHERE id=?", (existing[0],))
                match_id = existing[0]
            else:
                cur = await db.execute(
                    "INSERT INTO matches(user1_id,user2_id,status) VALUES (?, ?, 'matched')",
                    (liker_id, liked_id),
                )
                match_id = cur.lastrowid
            await db.commit()
            return True, match_id

    async def pass_like(self, liker_id: int, liked_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO likes(liker_id, liked_id) VALUES (?, ?)", (liker_id, liked_id))
            await db.commit()

    async def list_matches_for_user(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT m.id, m.status,
                       CASE WHEN m.user1_id=? THEN u2.name ELSE u1.name END AS partner_name,
                       CASE WHEN m.user1_id=? THEN u2.age ELSE u1.age END AS partner_age,
                       CASE WHEN m.user1_id=? THEN u2.city ELSE u1.city END AS partner_city
                FROM matches m
                JOIN users u1 ON u1.id=m.user1_id
                JOIN users u2 ON u2.id=m.user2_id
                WHERE (m.user1_id=? OR m.user2_id=?)
                ORDER BY m.updated_at DESC
                """,
                (user_id, user_id, user_id, user_id, user_id),
            ) as cur:
                rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def get_match_for_user(self, match_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)", (match_id, user_id, user_id)) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

    async def users_for_match(self, match_id: int) -> tuple[dict, dict] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user1_id,user2_id FROM matches WHERE id=?", (match_id,)) as c:
                m = await c.fetchone()
            if not m:
                return None
            async with db.execute("SELECT * FROM users WHERE id=?", (m[0],)) as c1:
                u1 = await c1.fetchone()
            async with db.execute("SELECT * FROM users WHERE id=?", (m[1],)) as c2:
                u2 = await c2.fetchone()
            if not u1 or not u2:
                return None
            return dict(u1), dict(u2)

    async def propose_game(self, match_id: int, proposer_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE matches SET status='game_invited', game_invited_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('matched','game_declined')",
                (proposer_id, match_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def accept_game(self, match_id: int) -> bool:
        prompt = TEXT_PROMPTS[0]
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE matches SET status='game_active', game_round=1, game_prompt=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (prompt, match_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def start_next_round(self, match_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT game_round FROM matches WHERE id=?", (match_id,)) as c:
                row = await c.fetchone()
            if not row:
                return None
            next_round = int(row["game_round"] or 0) + 1
            prompt_pool = TEXT_PROMPTS if next_round % 3 == 1 else (VOICE_PROMPTS if next_round % 3 == 2 else VIDEO_PROMPTS)
            prompt = prompt_pool[(next_round - 1) % len(prompt_pool)]
            await db.execute(
                "UPDATE matches SET game_round=?, game_prompt=?, status='game_active', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (next_round, prompt, match_id),
            )
            await db.commit()
            return {"round": next_round, "prompt": prompt}

    async def decline_game(self, match_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("UPDATE matches SET status='game_declined', updated_at=CURRENT_TIMESTAMP WHERE id=?", (match_id,))
            await db.commit()
            return cur.rowcount > 0

    async def save_round_answer(self, match_id: int, round_number: int, sender_user_id: int, message_type: str, text: str | None, file_id: str | None, prompt: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO match_messages(match_id, round_number, sender_user_id, message_type, text, file_id, prompt) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (match_id, round_number, sender_user_id, message_type, text, file_id, prompt),
            )
            await db.execute("UPDATE users SET reputation_score = reputation_score + 1 WHERE id=?", (sender_user_id,))
            await db.commit()

    async def get_round_answers(self, match_id: int, round_number: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM match_messages WHERE match_id=? AND round_number=? ORDER BY id", (match_id, round_number)) as c:
                rows = await c.fetchall()
            return [dict(r) for r in rows]

    async def round_answered_user_ids(self, match_id: int, round_number: int) -> set[int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT DISTINCT sender_user_id FROM match_messages WHERE match_id=? AND round_number=?",
                (match_id, round_number),
            ) as c:
                rows = await c.fetchall()
            return {int(r[0]) for r in rows}

    async def request_contact_reveal(self, match_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user1_id,user2_id FROM matches WHERE id=?", (match_id,)) as c:
                m = await c.fetchone()
            if not m:
                return False
            col = "user1_reveal_requested" if user_id == m[0] else "user2_reveal_requested"
            await db.execute(f"UPDATE matches SET {col}=1 WHERE id=?", (match_id,))
            await db.commit()
            return True

    async def accept_contact_reveal(self, match_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id=?", (match_id,)) as c:
                m = await c.fetchone()
            if not m:
                return False
            col = "user1_reveal_requested" if user_id == m["user1_id"] else "user2_reveal_requested"
            await db.execute(f"UPDATE matches SET {col}=1 WHERE id=?", (match_id,))
            async with db.execute("SELECT user1_reveal_requested,user2_reveal_requested FROM matches WHERE id=?", (match_id,)) as c2:
                rr = await c2.fetchone()
            if rr and rr[0] and rr[1]:
                await db.execute("UPDATE matches SET status='contact_revealed', contact_revealed_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (datetime.now(UTC).isoformat(), match_id))
                await db.execute("UPDATE users SET reputation_score = reputation_score + 3 WHERE id IN (?, ?)", (m["user1_id"], m["user2_id"]))
            await db.commit()
            return True

    async def close_match(self, match_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("UPDATE matches SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=?", (match_id,))
            await db.commit()
            return cur.rowcount > 0
