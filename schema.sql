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
CREATE TABLE IF NOT EXISTS flood_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_flood_lookup ON flood_events(chat_id, user_id, created_at);


-- 24/7 organic growth publishing targets. The first target is treated as a public channel,
-- the second as a public group; change target_type if the user's link roles are reversed.
CREATE TABLE IF NOT EXISTS growth_targets (
  target TEXT PRIMARY KEY,
  target_type TEXT NOT NULL CHECK(target_type IN ('channel','group')),
  interval_hours INTEGER NOT NULL DEFAULT 24,
  enabled INTEGER NOT NULL DEFAULT 1,
  last_sent_at TEXT,
  last_message_index INTEGER NOT NULL DEFAULT -1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO growth_targets(target, target_type, interval_hours, enabled)
VALUES ('@MyBazarek', 'channel', 8, 1), ('@mybazarek2026', 'group', 24, 1);

CREATE TABLE IF NOT EXISTS growth_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  target TEXT NOT NULL,
  target_type TEXT NOT NULL,
  message_index INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  error TEXT,
  sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_growth_posts_target_time ON growth_posts(target, sent_at);
