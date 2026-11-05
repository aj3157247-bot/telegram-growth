import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    owner_id: int = int(os.getenv("OWNER_ID", "0"))
    bot_name: str = os.getenv("BOT_NAME", "Growth Manager")
    db_path: str = os.getenv("DB_PATH", "data/bot.sqlite3")
    anti_link: bool = as_bool("ANTI_LINK", True)
    anti_flood: bool = as_bool("ANTI_FLOOD", True)
    flood_max_messages: int = int(os.getenv("FLOOD_MAX_MESSAGES", "5"))
    flood_window_seconds: int = int(os.getenv("FLOOD_WINDOW_SECONDS", "8"))
    welcome_enabled: bool = as_bool("WELCOME_ENABLED", True)
    blocked_words: tuple = tuple(
        w.strip().lower() for w in os.getenv("BLOCKED_WORDS", "").split(",") if w.strip()
    )

settings = Settings()
Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
