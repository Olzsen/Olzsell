import json
import os
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from app.config import ROOT_DIR, Settings

STORE_PATH = ROOT_DIR / "data" / "playerok_settings.json"
SECRET_FIELDS = {"token", "extra_cookies_json"}


def load_playerok_settings(settings: Settings) -> None:
    """Load bot-configured Playerok credentials from a local, gitignored file."""
    try:
        data: dict[str, Any] = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError):
        raise RuntimeError(
            f"Could not read {STORE_PATH}. Check the file and its JSON format."
        )
    token = data.get("token")
    user_agent = data.get("user_agent")
    cookies = data.get("extra_cookies_json")
    mode = data.get("mode")
    if isinstance(token, str):
        settings.playerok_token = SecretStr(token) if token else None
    if isinstance(user_agent, str):
        settings.playerok_user_agent = user_agent
    if isinstance(cookies, str):
        settings.playerok_extra_cookies_json = SecretStr(cookies) if cookies else None
    if mode in {"demo", "live"}:
        settings.playerok_mode = mode


def save_playerok_settings(settings: Settings) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "token": settings.playerok_token.get_secret_value() if settings.playerok_token else "",
        "user_agent": settings.playerok_user_agent,
        "extra_cookies_json": (
            settings.playerok_extra_cookies_json.get_secret_value()
            if settings.playerok_extra_cookies_json else ""
        ),
        "mode": settings.playerok_mode,
    }
    temporary = STORE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(STORE_PATH)
