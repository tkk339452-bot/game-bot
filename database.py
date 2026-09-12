import aiosqlite

DB_NAME = "game.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0,
                last_work INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0,
                last_business_income INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                quantity INTEGER DEFAULT 1,
                UNIQUE(user_id, item_name)
            )
        """)
        await db.commit()


async def get_user(user_id: int, username: str = None):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user is None:
                from config import START_BALANCE
                await db.execute(
                    "INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                    (user_id, username or "Unknown", START_BALANCE)
                )
                await db.commit()
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as c2:
                    user = await c2.fetchone()
            return dict(user)


async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        if amount > 0:
            await db.execute(
                "UPDATE users SET total_earned = total_earned + ? WHERE user_id = ?",
                (amount, user_id)
            )
        await db.commit()


async def update_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            f"UPDATE users SET {field} = ? WHERE user_id = ?",
            (value, user_id)
        )
        await db.commit()


async def add_item(user_id: int, item_name: str, qty: int = 1):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT quantity FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_name = ?",
                    (qty, user_id, item_name)
                )
            else:
                await db.execute(
                    "INSERT INTO inventory (user_id, item_name, quantity) VALUES (?, ?, ?)",
                    (user_id, item_name, qty)
                )
        await db.commit()


async def remove_item(user_id: int, item_name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item_name = ?",
            (user_id, item_name)
        )
        await db.commit()


async def get_inventory(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT item_name, quantity FROM inventory WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def get_top(limit: int = 10):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT username, balance FROM users ORDER BY balance DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]