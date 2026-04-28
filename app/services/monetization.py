from __future__ import annotations

import aiosqlite


class MonetizationService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def list_active_plans(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT code, title, stars_amount, price_rub FROM monetization_plans WHERE is_active=1 ORDER BY price_rub"
            ) as cur:
                rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def create_pending_payment(self, user_id: int, plan_code: str) -> int | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT code, price_rub, stars_amount FROM monetization_plans WHERE code=? AND is_active=1",
                (plan_code,),
            ) as cur:
                plan = await cur.fetchone()
            if not plan:
                return None
            cur = await db.execute(
                """
                INSERT INTO payments(user_id, plan_code, amount_rub, stars_amount, status, provider)
                VALUES (?, ?, ?, ?, 'pending', 'stub')
                """,
                (user_id, plan["code"], plan["price_rub"], plan["stars_amount"]),
            )
            await db.commit()
            return int(cur.lastrowid)

    async def mark_payment_paid(self, payment_id: int, external_payment_id: str | None = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, user_id, stars_amount, status FROM payments WHERE id=?",
                (payment_id,),
            ) as cur:
                payment = await cur.fetchone()
            if not payment or payment["status"] == "paid":
                return False
            cur = await db.execute(
                "UPDATE payments SET status='paid', external_payment_id=? WHERE id=? AND status='pending'",
                (external_payment_id, payment_id),
            )
            if cur.rowcount == 0:
                await db.commit()
                return False
            await db.execute(
                "UPDATE users SET stars_balance = stars_balance + ? WHERE id=?",
                (payment["stars_amount"], payment["user_id"]),
            )
            await db.commit()
            return True
