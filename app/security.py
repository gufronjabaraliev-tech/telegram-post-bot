import hmac
import hashlib
import json
import urllib.parse
from typing import Optional, Dict, Any, Tuple
from app.config import BOT_TOKEN

def verify_telegram_init_data(init_data_raw: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifies Telegram WebApp initData using HMAC-SHA256.
    Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data_raw:
        return False, None

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        if "hash" not in parsed_data:
            return False, None

        received_hash = parsed_data.pop("hash")

        # Sort parameters alphabetically
        data_check_items = []
        for key in sorted(parsed_data.keys()):
            data_check_items.append(f"{key}={parsed_data[key]}")
        data_check_string = "\n".join(data_check_items)

        # secret_key = HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # calculated_hash = HMAC_SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        if calculated_hash != received_hash:
            return False, None

        # Extract user object if present
        user_info = None
        if "user" in parsed_data:
            user_info = json.loads(parsed_data["user"])

        return True, user_info
    except Exception as e:
        return False, None
