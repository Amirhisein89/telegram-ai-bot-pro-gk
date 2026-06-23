# ============================
#        database.py
# ============================

import aiosqlite
import datetime
from config import DB_NAME, SUBSCRIPTION_DAYS


async def init_db():
    """ساخت جداول دیتابیس در اولین اجرا"""
    async with aiosqlite.connect(DB_NAME) as db:
        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TEXT,
                sub_code    TEXT,
                sub_expires TEXT
            )
        """)
        # جدول کدهای اشتراک
        await db.execute("""
            CREATE TABLE IF NOT EXISTS codes (
                code        TEXT PRIMARY KEY,
                used        INTEGER DEFAULT 0,
                used_by     INTEGER,
                used_at     TEXT
            )
        """)
        await db.commit()


# ─── کاربران ───────────────────────────────────────────

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone()


async def upsert_user(user_id: int, username: str, first_name: str):
    """ثبت کاربر جدید یا بروزرسانی اطلاعاتش"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name,
              datetime.datetime.now().isoformat()))
        await db.commit()


async def is_subscribed(user_id: int) -> bool:
    """بررسی اینکه اشتراک کاربر فعال است یا نه"""
    user = await get_user(user_id)
    if not user or not user["sub_expires"]:
        return False
    expires = datetime.datetime.fromisoformat(user["sub_expires"])
    return datetime.datetime.now() < expires


async def activate_subscription(user_id: int, code: str) -> bool:
    """
    فعال‌سازی اشتراک با کد.
    برمی‌گرداند True اگر موفق، False اگر کد نامعتبر/استفاده‌شده باشد.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute(
            "SELECT * FROM codes WHERE code = ?", (code,)
        ) as cur:
            row = await cur.fetchone()

        if not row or row["used"]:
            return False

        now = datetime.datetime.now()
        await db.execute("""
            UPDATE codes SET used = 1, used_by = ?, used_at = ?
            WHERE code = ?
        """, (user_id, now.isoformat(), code))

        expires = now + datetime.timedelta(days=SUBSCRIPTION_DAYS)
        await db.execute("""
            UPDATE users SET sub_code = ?, sub_expires = ?
            WHERE user_id = ?
        """, (code, expires.isoformat(), user_id))

        await db.commit()
        return True


async def subscription_info(user_id: int):
    """برگرداندن تاریخ انقضا و روزهای باقیمانده"""
    user = await get_user(user_id)
    if not user or not user["sub_expires"]:
        return None, None
    expires = datetime.datetime.fromisoformat(user["sub_expires"])
    remaining = (expires - datetime.datetime.now()).days
    return expires, max(remaining, 0)


async def add_code(code: str) -> bool:
    """اضافه کردن کد جدید توسط ادمین"""
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO codes (code) VALUES (?)", (code,)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False  # کد تکراری


async def delete_code(code: str) -> bool:
    """حذف کد توسط ادمین"""
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "DELETE FROM codes WHERE code = ?", (code,)
        )
        await db.commit()
        return cur.rowcount > 0


async def list_codes():
    """لیست همه کدها"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM codes ORDER BY used") as cur:
            return await cur.fetchall()


async def list_users():
    """لیست همه کاربران"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users ORDER BY joined_at DESC"
        ) as cur:
            return await cur.fetchall()
