import aiosqlite
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    chat_type TEXT NOT NULL,
    username TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS members (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    first_name TEXT,
    status TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at TEXT,
    PRIMARY KEY (chat_id, user_id)
);
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    admin_id INTEGER,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS invite_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    invite_link TEXT NOT NULL UNIQUE,
    label TEXT,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    actor_id INTEGER,
    event TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn = None

    async def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def execute(self, query, params=()):
        cur = await self.conn.execute(query, params)
        await self.conn.commit()
        return cur

    async def fetchall(self, query, params=()):
        cur = await self.conn.execute(query, params)
        return await cur.fetchall()

    async def fetchone(self, query, params=()):
        cur = await self.conn.execute(query, params)
        return await cur.fetchone()

    async def upsert_chat(self, chat):
        await self.execute(
            """INSERT INTO chats(chat_id,title,chat_type,username,is_active)
               VALUES(?,?,?,?,1)
               ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,
               chat_type=excluded.chat_type, username=excluded.username, is_active=1""",
            (chat.id, chat.title or str(chat.id), chat.type.value, chat.username),
        )

    async def log(self, chat_id, actor_id, event, details=""):
        await self.execute(
            "INSERT INTO activity_logs(chat_id,actor_id,event,details) VALUES(?,?,?,?)",
            (chat_id, actor_id, event, details),
        )

    async def close(self):
        if self.conn:
            await self.conn.close()
