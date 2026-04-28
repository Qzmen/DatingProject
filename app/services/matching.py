from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta

import aiosqlite

ROUND_TIMER_SECONDS = 120
PAIR_COOLDOWN_HOURS = 24
ACTIVE_INTERACTION_STATUSES = {
    "matched",
    "game_invited",
    "waiting_game_accept",
    "game_active",
    "reveal_pending",
}

PROMPTS: dict[str, list[str]] = {
    "text": [
        "Опиши свой сегодняшний вайб тремя словами.",
        "Что тебя обычно цепляет в людях с первых минут?",
        "Если бы у вас была прогулка на 30 минут, куда бы ты предложил(а) пойти?",
        "Какой неожиданный факт о тебе стоит узнать?",
        "Что для тебя важнее в общении: юмор, спокойствие или энергия?",
    ],
    "voice": [
        "Отправь голосовое до 30 секунд: какой у тебя сегодня настрой?",
        "Расскажи голосом один неожиданный факт о себе.",
        "Скажи голосом фразу, которая тебя лучше всего описывает.",
    ],
    "video_note": [
        "Запиши кружок с коротким приветствием.",
        "Запиши кружок: кофе или чай?",
        "Покажи в кружке реакцию на этот матч.",
    ],
    "photo": [
        "Отправь фото из галереи: предмет, который описывает твой сегодняшний день.",
        "Отправь фото места, где тебе уютно.",
        "Отправь фото без лица: деталь, которая передаёт твой вайб.",
    ],
    "any": [
        "Расскажи о себе удобным способом: текстом, голосом, кружком или фото.",
        "Поделись своим настроением любым форматом.",
    ],
}

CHOICE_PROMPTS: list[tuple[str, list[str]]] = [
    ("Выбери: кофе или чай?", ["☕ Кофе", "🍵 Чай"]),
    ("Выбери: кино или прогулка?", ["🎬 Кино", "🚶 Прогулка"]),
    ("Выбери: план или спонтанность?", ["🗂 План", "⚡ Спонтанность"]),
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

    async def next_candidate(self, user_id: int, city_normalized: str, same_city_only: bool = True) -> dict | None:
        placeholders = ",".join("?" for _ in ACTIVE_INTERACTION_STATUSES)
        params: list[object] = [user_id]
        query = f"""
            SELECT id, tg_id, name, age, city, description, photo_file_id, voice_file_id, video_note_file_id, reputation_score
            FROM users candidate
            WHERE candidate.id != ?
              AND candidate.is_blocked = 0
              AND candidate.is_profile_enabled = 1
              AND NOT EXISTS (
                SELECT 1
                FROM matches m
                WHERE ((m.user1_id = ? AND m.user2_id = candidate.id) OR (m.user1_id = candidate.id AND m.user2_id = ?))
                  AND m.status IN ({placeholders})
              )
              AND NOT EXISTS (
                SELECT 1
                FROM pair_cooldowns pc
                WHERE pc.user1_id = CASE WHEN ? < candidate.id THEN ? ELSE candidate.id END
                  AND pc.user2_id = CASE WHEN ? < candidate.id THEN candidate.id ELSE ? END
                  AND datetime(pc.expires_at) > datetime('now')
              )
        """
        params.extend([user_id, user_id, *ACTIVE_INTERACTION_STATUSES, user_id, user_id, user_id, user_id])
        if same_city_only:
            query += """
            AND COALESCE(NULLIF(candidate.city_normalized, ''), lower(replace(trim(candidate.city), 'ё', 'е'))) = ?
            """
            params.append(city_normalized)
        query += " ORDER BY RANDOM() LIMIT 1"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

    async def _find_active_match(self, db: aiosqlite.Connection, user_a: int, user_b: int) -> dict | None:
        db.row_factory = aiosqlite.Row
        placeholders = ",".join("?" for _ in ACTIVE_INTERACTION_STATUSES)
        sql = f"""
            SELECT * FROM matches
            WHERE ((user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?))
              AND status IN ({placeholders})
            ORDER BY id DESC LIMIT 1
        """
        async with db.execute(sql, (user_a, user_b, user_b, user_a, *ACTIVE_INTERACTION_STATUSES)) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    @staticmethod
    def _ordered_pair(user_a: int, user_b: int) -> tuple[int, int]:
        return (user_a, user_b) if user_a < user_b else (user_b, user_a)

    async def _upsert_pair_cooldown(self, db: aiosqlite.Connection, user_a: int, user_b: int, reason: str) -> None:
        p1, p2 = self._ordered_pair(user_a, user_b)
        expires_at = (datetime.now(UTC) + timedelta(hours=PAIR_COOLDOWN_HOURS)).isoformat()
        await db.execute(
            """
            INSERT INTO pair_cooldowns(user1_id, user2_id, reason, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user1_id, user2_id) DO UPDATE SET
                reason=excluded.reason,
                expires_at=excluded.expires_at,
                created_at=CURRENT_TIMESTAMP
            """,
            (p1, p2, reason, expires_at),
        )

    async def like(self, liker_id: int, liked_id: int) -> tuple[bool, int | None, bool]:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO likes(liker_id, liked_id) VALUES (?, ?)", (liker_id, liked_id))
            new_like_created = db.total_changes > 0

            async with db.execute("SELECT 1 FROM likes WHERE liker_id=? AND liked_id=?", (liked_id, liker_id)) as cur:
                reciprocal = await cur.fetchone()
            if not reciprocal:
                await db.commit()
                return False, None, new_like_created

            active = await self._find_active_match(db, liker_id, liked_id)
            if active:
                await db.commit()
                return True, int(active["id"]), new_like_created

            async with db.execute(
                "SELECT id FROM matches WHERE ((user1_id=? AND user2_id=?) OR (user1_id=? AND user2_id=?)) ORDER BY id DESC LIMIT 1",
                (liker_id, liked_id, liked_id, liker_id),
            ) as cur:
                existing_any = await cur.fetchone()
            if existing_any:
                match_id = int(existing_any[0])
                await db.execute(
                    """
                    UPDATE matches
                    SET status='matched',
                        game_round=0,
                        game_prompt=NULL,
                        expected_answer_type='text',
                        choice_options=NULL,
                        user1_reveal_requested=0,
                        user2_reveal_requested=0,
                        contact_revealed_at=NULL,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (match_id,),
                )
            else:
                cur = await db.execute("INSERT INTO matches(user1_id,user2_id,status) VALUES (?, ?, 'matched')", (liker_id, liked_id))
                match_id = int(cur.lastrowid)
            await self._upsert_pair_cooldown(db, liker_id, liked_id, "match_created")
            await db.commit()
            return True, match_id, new_like_created

    async def pass_like(self, liker_id: int, liked_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO likes(liker_id, liked_id) VALUES (?, ?)", (liker_id, liked_id))
            await db.commit()

    async def list_matches_for_user(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT m.id, m.status, m.game_round,
                       CASE WHEN m.user1_id=? THEN u2.name ELSE u1.name END AS partner_name,
                       CASE WHEN m.user1_id=? THEN u2.age ELSE u1.age END AS partner_age,
                       CASE WHEN m.user1_id=? THEN u2.city ELSE u1.city END AS partner_city,
                       CASE WHEN m.user1_id=? THEN u2.username ELSE u1.username END AS partner_username,
                       CASE WHEN m.user1_id=? THEN u2.tg_id ELSE u1.tg_id END AS partner_tg_id
                FROM matches m
                JOIN users u1 ON u1.id=m.user1_id
                JOIN users u2 ON u2.id=m.user2_id
                WHERE (m.user1_id=? OR m.user2_id=?)
                ORDER BY m.updated_at DESC
                """,
                (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id),
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

    def _random_round_payload(self, round_number: int) -> tuple[str, str, list[str] | None]:
        cycle = ["text", "voice", "video_note", "photo", "choice", "any"]
        answer_type = cycle[(round_number - 1) % len(cycle)]
        if answer_type == "choice":
            prompt, options = random.choice(CHOICE_PROMPTS)
            return prompt, answer_type, options
        prompt = random.choice(PROMPTS[answer_type])
        return prompt, answer_type, None

    async def propose_game(self, match_id: int, proposer_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE matches SET status='game_invited', game_invited_by=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status IN ('matched','game_declined')",
                (proposer_id, match_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def accept_game(self, match_id: int) -> dict | None:
        prompt, answer_type, options = self._random_round_payload(1)
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=ROUND_TIMER_SECONDS)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                UPDATE matches
                SET status='game_active', game_round=1, game_prompt=?, expected_answer_type=?, choice_options=?,
                    round_started_at=?, round_expires_at=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='game_invited'
                """,
                (prompt, answer_type, json.dumps(options) if options else None, now.isoformat(), expires.isoformat(), match_id),
            )
            if cur.rowcount == 0:
                await db.commit()
                return None
            await db.execute("DELETE FROM match_messages WHERE match_id=? AND round_number=1", (match_id,))
            await db.commit()
            return {"round": 1, "prompt": prompt, "expected_answer_type": answer_type, "choice_options": options}

    async def start_next_round(self, match_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id=?", (match_id,)) as cur:
                m = await cur.fetchone()
            if not m or m["status"] != "game_active":
                return None
            current_round = int(m["game_round"] or 1)
            async with db.execute(
                "SELECT COUNT(DISTINCT sender_user_id) FROM match_messages WHERE match_id=? AND round_number=?",
                (match_id, current_round),
            ) as cur:
                answered_count = int((await cur.fetchone())[0])
            if answered_count < 2:
                return None
            prompt, answer_type, options = self._random_round_payload(current_round + 1)
            now = datetime.now(UTC)
            expires = now + timedelta(seconds=ROUND_TIMER_SECONDS)
            cur = await db.execute(
                """
                UPDATE matches
                SET game_round=?, game_prompt=?, expected_answer_type=?, choice_options=?, round_started_at=?, round_expires_at=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='game_active' AND game_round=?
                """,
                (current_round + 1, prompt, answer_type, json.dumps(options) if options else None, now.isoformat(), expires.isoformat(), match_id, current_round),
            )
            await db.commit()
            if cur.rowcount == 0:
                return None
            return {"round": current_round + 1, "prompt": prompt, "expected_answer_type": answer_type, "choice_options": options}

    async def create_or_refresh_challenge(self, match_id: int) -> dict | None:
        texts = [
            "Сфоткайте самый уютный угол дома и обменяйтесь снимками.",
            "Сделайте фото вашего идеального напитка вечера.",
            "Покажите в фото вещь, которая описывает ваш характер.",
        ]
        challenge_text = random.choice(texts)
        expires = datetime.now(UTC) + timedelta(hours=24)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE matches SET challenge_text=?, challenge_expires_at=?, challenge_user1_done=0, challenge_user2_done=0, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='game_active'",
                (challenge_text, expires.isoformat(), match_id),
            )
            await db.commit()
            if cur.rowcount == 0:
                return None
            return {"text": challenge_text, "expires_at": expires.isoformat()}

    async def complete_challenge(self, match_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user1_id, user2_id, challenge_user1_done, challenge_user2_done FROM matches WHERE id=?", (match_id,)) as cur:
                row = await cur.fetchone()
            if not row:
                return None
            col = "challenge_user1_done" if user_id == row["user1_id"] else "challenge_user2_done"
            await db.execute(f"UPDATE matches SET {col}=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (match_id,))
            async with db.execute("SELECT challenge_user1_done, challenge_user2_done, user1_id, user2_id FROM matches WHERE id=?", (match_id,)) as cur2:
                state = await cur2.fetchone()
            if state and state["challenge_user1_done"] and state["challenge_user2_done"]:
                await db.execute("UPDATE users SET reputation_score = reputation_score + 2 WHERE id IN (?, ?)", (state["user1_id"], state["user2_id"]))
            await db.commit()
            return dict(state) if state else None

    async def decline_game(self, match_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("UPDATE matches SET status='game_declined', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='game_invited'", (match_id,))
            await db.commit()
            return cur.rowcount > 0

    async def get_active_game_for_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM matches WHERE status='game_active' AND (user1_id=? OR user2_id=?) ORDER BY updated_at DESC LIMIT 1",
                (user_id, user_id),
            ) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None

    async def round_answered_user_ids(self, match_id: int, round_number: int) -> set[int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT DISTINCT sender_user_id FROM match_messages WHERE match_id=? AND round_number=?", (match_id, round_number)) as c:
                rows = await c.fetchall()
            return {int(r[0]) for r in rows}

    async def save_round_answer(
        self,
        match_id: int,
        round_number: int,
        sender_user_id: int,
        message_type: str,
        text: str | None,
        file_id: str | None,
        prompt: str,
    ) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT status FROM matches WHERE id=?", (match_id,)) as cur:
                match_row = await cur.fetchone()
            if not match_row or match_row["status"] != "game_active":
                return "stale"
            async with db.execute(
                "SELECT id FROM match_messages WHERE match_id=? AND round_number=? AND sender_user_id=? LIMIT 1",
                (match_id, round_number, sender_user_id),
            ) as cur:
                existing = await cur.fetchone()
            if existing:
                return "duplicate"
            await db.execute(
                "INSERT INTO match_messages(match_id, round_number, sender_user_id, message_type, text, file_id, prompt) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (match_id, round_number, sender_user_id, message_type, text, file_id, prompt),
            )
            await db.execute("UPDATE users SET reputation_score = reputation_score + 1 WHERE id=?", (sender_user_id,))
            await db.commit()
            return "saved"

    async def get_round_answers(self, match_id: int, round_number: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM match_messages WHERE match_id=? AND round_number=? ORDER BY id", (match_id, round_number)) as c:
                rows = await c.fetchall()
            return [dict(r) for r in rows]

    async def get_undelivered_round_answers(self, match_id: int, round_number: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM match_messages WHERE match_id=? AND round_number=? AND delivered_to_partner=0 ORDER BY id",
                (match_id, round_number),
            ) as c:
                rows = await c.fetchall()
            return [dict(r) for r in rows]

    async def mark_round_answers_delivered(self, match_id: int, round_number: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE match_messages SET delivered_to_partner=1 WHERE match_id=? AND round_number=?",
                (match_id, round_number),
            )
            await db.commit()

    async def request_contact_reveal(self, match_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user1_id,user2_id,status FROM matches WHERE id=?", (match_id,)) as c:
                m = await c.fetchone()
            if not m or m["status"] not in {"game_active", "matched", "game_declined", "contact_revealed"}:
                return False
            col = "user1_reveal_requested" if user_id == m["user1_id"] else "user2_reveal_requested"
            cur = await db.execute(f"UPDATE matches SET {col}=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (match_id,))
            await db.commit()
            return cur.rowcount > 0

    async def accept_contact_reveal(self, match_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM matches WHERE id=?", (match_id,)) as c:
                m = await c.fetchone()
            if not m:
                return False
            col = "user1_reveal_requested" if user_id == m["user1_id"] else "user2_reveal_requested"
            await db.execute(f"UPDATE matches SET {col}=1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (match_id,))
            async with db.execute("SELECT user1_reveal_requested,user2_reveal_requested FROM matches WHERE id=?", (match_id,)) as c2:
                rr = await c2.fetchone()
            if rr and rr[0] and rr[1]:
                await db.execute(
                    "UPDATE matches SET status='contact_revealed', contact_revealed_at=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND status!='closed'",
                    (datetime.now(UTC).isoformat(), match_id),
                )
                await db.execute("UPDATE users SET reputation_score = reputation_score + 3 WHERE id IN (?, ?)", (m["user1_id"], m["user2_id"]))
            await db.commit()
            return True

    async def close_match(self, match_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("UPDATE matches SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status!='closed'", (match_id,))
            await db.commit()
            return cur.rowcount > 0

    async def end_game(self, match_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE matches SET status='game_ended', updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='game_active'",
                (match_id,),
            )
            await db.commit()
            return cur.rowcount > 0
