import hashlib
import hmac
import json
from urllib.parse import parse_qs, unquote

import config


def validate_telegram_data(init_data: str) -> dict | None:
    if not init_data:
        return None

    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None

        data_pairs = []
        for key, values in parsed.items():
            if key == "hash":
                continue
            data_pairs.append(f"{key}={unquote(values[0])}")

        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)

        secret_key = hmac.new(
            b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256
        ).digest()

        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        user_data_str = parsed.get("user", [None])[0]
        if not user_data_str:
            return None

        user_data = json.loads(unquote(user_data_str))
        return {
            "user_id": user_data.get("id"),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "username": user_data.get("username", ""),
        }
    except Exception:
        return None
