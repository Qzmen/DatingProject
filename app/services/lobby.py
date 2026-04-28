from __future__ import annotations

import random
import string

import aiosqlite


class LobbyService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def ensure_user_not_in_active_lobby(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE lobby_members SET status='left', left_at=CURRENT_TIMESTAMP WHERE user_id=? AND status='active'",
                (user_id,),
            )
            await db.commit()

    async def list_lobbies(self, city_normalized: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT l.id, l.title, l.max_players, l.visibility, l.status, COUNT(lm.id) AS players
                FROM lobbies l
                LEFT JOIN lobby_members lm ON lm.lobby_id=l.id AND lm.status='active'
                WHERE l.city_normalized=? AND l.status IN ('waiting','active') AND l.visibility='public'
                GROUP BY l.id
                ORDER BY l.created_at DESC
                """,
                (city_normalized,),
            ) as cur:
                rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def create_lobby(self, owner_user_id: int, city: str, city_normalized: str, title: str, max_players: int, visibility: str) -> dict:
        invite_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6)) if visibility == "private" else None
        await self.ensure_user_not_in_active_lobby(owner_user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "INSERT INTO lobbies(city, city_normalized, title, owner_user_id, max_players, visibility, invite_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')",
                (city, city_normalized, title, owner_user_id, max_players, visibility, invite_code),
            )
            lobby_id = int(cur.lastrowid)
            await db.execute(
                "INSERT INTO lobby_members(lobby_id, user_id, role, status, joined_at) VALUES (?, ?, 'host', 'active', CURRENT_TIMESTAMP)",
                (lobby_id, owner_user_id),
            )
            await db.commit()
        return {"id": lobby_id, "invite_code": invite_code}

    async def join_lobby(self, user_id: int, lobby_id: int) -> bool:
        await self.ensure_user_not_in_active_lobby(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM lobbies WHERE id=? AND status IN ('waiting','active')", (lobby_id,)) as cur:
                lobby = await cur.fetchone()
            if not lobby:
                return False
            async with db.execute("SELECT city_normalized, is_blocked FROM users WHERE id=?", (user_id,)) as cur:
                user = await cur.fetchone()
            if not user or user["is_blocked"] or user["city_normalized"] != lobby["city_normalized"]:
                return False
            async with db.execute("SELECT COUNT(*) FROM lobby_members WHERE lobby_id=? AND status='active'", (lobby_id,)) as cur:
                cnt = int((await cur.fetchone())[0])
            if cnt >= int(lobby["max_players"]):
                return False
            await db.execute(
                """
                INSERT INTO lobby_members(lobby_id, user_id, role, status, joined_at, left_at)
                VALUES (?, ?, 'member', 'active', CURRENT_TIMESTAMP, NULL)
                ON CONFLICT(lobby_id, user_id) DO UPDATE SET status='active', left_at=NULL, joined_at=CURRENT_TIMESTAMP
                """,
                (lobby_id, user_id),
            )
            await db.commit()
            return True

    async def join_lobby_by_code(self, user_id: int, invite_code: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM lobbies WHERE invite_code=? AND status IN ('waiting','active')", (invite_code.upper(),)) as cur:
                row = await cur.fetchone()
        if not row:
            return False
        return await self.join_lobby(user_id, int(row[0]))

    async def leave_lobby(self, user_id: int, lobby_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE lobby_members SET status='left', left_at=CURRENT_TIMESTAMP WHERE lobby_id=? AND user_id=? AND status='active'",
                (lobby_id, user_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def start_lobby(self, owner_user_id: int, lobby_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "UPDATE lobbies SET status='active', updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner_user_id=? AND status='waiting'",
                (lobby_id, owner_user_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def get_lobby_state(self, lobby_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM lobbies WHERE id=?", (lobby_id,)) as cur:
                lobby = await cur.fetchone()
            if not lobby:
                return None
            async with db.execute(
                """
                SELECT u.id, u.name, u.age, u.city, u.description, u.reputation_score, lm.role
                FROM lobby_members lm
                JOIN users u ON u.id=lm.user_id
                WHERE lm.lobby_id=? AND lm.status='active'
                ORDER BY lm.role DESC, lm.joined_at
                """,
                (lobby_id,),
            ) as cur:
                members = await cur.fetchall()
            return {"lobby": dict(lobby), "members": [dict(m) for m in members]}

    async def active_lobby_for_user(self, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT l.*, lm.role
                FROM lobby_members lm
                JOIN lobbies l ON l.id=lm.lobby_id
                WHERE lm.user_id=? AND lm.status='active' AND l.status IN ('waiting','active')
                ORDER BY lm.joined_at DESC LIMIT 1
                """,
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
            return dict(row) if row else None


class BottleService:
    def __init__(self, db_path: str, matching_service) -> None:
        self.db_path = db_path
        self.matching_service = matching_service

    async def spin(self, lobby_id: int, spinner_user_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT user_id FROM lobby_members WHERE lobby_id=? AND status='active' AND user_id!=?",
                (lobby_id, spinner_user_id),
            ) as cur:
                rows = await cur.fetchall()
            if not rows:
                return None
            selected_user_id = int(random.choice(rows)[0])
            angle = random.uniform(0, 360)
            cur = await db.execute(
                "INSERT INTO bottle_spins(lobby_id, spinner_user_id, selected_user_id, angle, status) VALUES (?, ?, ?, ?, 'created')",
                (lobby_id, spinner_user_id, selected_user_id, angle),
            )
            await db.commit()
            return {"spin_id": int(cur.lastrowid), "selected_user_id": selected_user_id, "angle": angle}

    async def like_from_spin(self, spin_id: int, from_user_id: int) -> tuple[bool, int | None, int | None]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bottle_spins WHERE id=?", (spin_id,)) as cur:
                spin = await cur.fetchone()
            if not spin or int(spin["spinner_user_id"]) != from_user_id:
                return False, None, None
            to_user_id = int(spin["selected_user_id"])
            await db.execute(
                "INSERT OR IGNORE INTO bottle_interactions(spin_id, from_user_id, to_user_id, action) VALUES (?, ?, ?, 'like')",
                (spin_id, from_user_id, to_user_id),
            )
            await db.commit()
        is_match, match_id, _ = await self.matching_service.like(from_user_id, to_user_id)
        return is_match, match_id, to_user_id
