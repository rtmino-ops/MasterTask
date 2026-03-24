import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'none',
                rating REAL DEFAULT 5.0,
                reviews_count INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                balance REAL DEFAULT 0.0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT '',
                budget REAL NOT NULL,
                deadline TEXT DEFAULT '',
                location TEXT DEFAULT '',
                status TEXT DEFAULT 'pending_review',
                executor_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                executor_id INTEGER,
                message TEXT DEFAULT '',
                proposed_price REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (executor_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL,
                tx_type TEXT DEFAULT 'escrow',
                status TEXT DEFAULT 'held',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS disputes (
                dispute_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                opened_by INTEGER,
                reason TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                resolution TEXT DEFAULT '',
                admin_comment TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                from_user INTEGER,
                to_user INTEGER,
                rating INTEGER DEFAULT 5,
                comment TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    print("DB OK")


async def execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def fetchone(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return await cursor.fetchone()


async def fetchall(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        return await cursor.fetchall()