import hashlib
import hmac
import os
import time
from typing import Dict
from urllib.parse import parse_qsl


class TelegramAuthError(Exception):
    pass


def _get_bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramAuthError("TELEGRAM_BOT_TOKEN is not set")
    return token


def verify_init_data(init_data: str, max_age_seconds: int = 86400) -> Dict[str, str]:
    if not init_data:
        raise TelegramAuthError("initData is empty")

    data = dict(parse_qsl(init_data, strict_parsing=True))
    if "hash" not in data:
        raise TelegramAuthError("initData hash missing")

    received_hash = data.pop("hash")
    data.pop("signature", None)

    auth_date_str = data.get("auth_date")
    if not auth_date_str:
        raise TelegramAuthError("initData auth_date missing")

    try:
        auth_date = int(auth_date_str)
    except ValueError as exc:
        raise TelegramAuthError("initData auth_date invalid") from exc

    now = int(time.time())
    if now - auth_date > max_age_seconds:
        raise TelegramAuthError("initData is слишком старый")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    bot_token = _get_bot_token().encode("utf-8")
    # Telegram Mini App verification:
    # secret_key = HMAC_SHA256(bot_token, key="WebAppData")
    secret_key = hmac.new(b"WebAppData", bot_token, hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramAuthError("initData signature invalid")

    return data
