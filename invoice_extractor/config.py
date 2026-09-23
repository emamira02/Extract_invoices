"""Application settings, read from environment variables (or a local .env file).

On Streamlit Community Cloud, root-level entries in the app's *Secrets* are exposed
as environment variables too, so the same code works locally and in the cloud.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    azure_endpoint: str = ""
    azure_key: str = ""
    locale: str = "it-IT"
    db_path: Path = PROJECT_ROOT / "history.db"
    history_limit: int = 10
    max_upload_mb: int = 10
    allowed_emails: frozenset[str] = field(default_factory=frozenset)

    @property
    def azure_configured(self) -> bool:
        return bool(self.azure_endpoint and self.azure_key)


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def load_settings() -> Settings:
    """Build Settings from the environment. Never hard-code keys in the source."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    emails = os.getenv("ALLOWED_EMAILS", "")
    return Settings(
        azure_endpoint=os.getenv("AZURE_DOCINTEL_ENDPOINT", "").strip(),
        azure_key=os.getenv("AZURE_DOCINTEL_KEY", "").strip(),
        locale=os.getenv("DOCINTEL_LOCALE", "it-IT").strip() or "it-IT",
        db_path=Path(os.getenv("HISTORY_DB_PATH", str(PROJECT_ROOT / "history.db"))),
        history_limit=_int("HISTORY_LIMIT", 10),
        max_upload_mb=_int("MAX_UPLOAD_MB", 10),
        allowed_emails=frozenset(e.strip().lower() for e in emails.split(",") if e.strip()),
    )
