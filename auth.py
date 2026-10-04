import hmac
import hashlib
import json
import urllib.parse
from typing import Optional, Dict, Any
import config


def validate_telegram_data(init_data: str) -> Optional[Dict[str, Any]]:
    """
    بررسی و اعتبارسنجی رشته initData ارسالی از Telegram Mini App
    بر اساس الگوریتم رسمی HMAC-SHA256 تلگرام
    """
    if not init_data:
        return None

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")

        # مرتب‌سازی کلیدها به ترتیب حروف الفبا
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )

        # ساخت کلید مخفی با توکن ربات
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=config.BOT_TOKEN.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()

        # محاسبه هش
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        # مقایسه هش‌ها
        if calculated_hash != received_hash:
            return None

        # استخراج آبجکت کاربر
        if "user" in parsed_data:
            user_info = json.loads(parsed_data["user"])
            return user_info

        return None
    except Exception:
        return None