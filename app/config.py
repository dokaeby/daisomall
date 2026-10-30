from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    database_type: str = "sqlite"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-please"
    session_days: int = 7


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def load_settings() -> Settings:
    _load_dotenv()
    return Settings(
        database_type=os.environ.get("DATABASE_TYPE", "sqlite"),
        database_path=Path(os.environ.get("DATABASE_PATH", "./shop.db")),
        admin_email=os.environ.get("ADMIN_EMAIL", "admin@example.com"),
        admin_password=os.environ.get("ADMIN_PASSWORD", "change-me-please"),
        session_days=int(os.environ.get("SESSION_DAYS", "7")),
    )
