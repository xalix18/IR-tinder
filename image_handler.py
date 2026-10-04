import os
import io
import hashlib
from pathlib import Path
from PIL import Image
from typing import Optional, Dict, Any
import config


def validate_image_bytes(image_bytes: bytes) -> bool:
    """اعتبارسنجی واقعی بودن فرمت تصویر"""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
            return img.format.lower() in config.ALLOWED_EXTENSIONS
    except Exception:
        return False


def compute_hash(image_bytes: bytes) -> str:
    """محاسبه هش SHA-256 برای جلوگیری از آپلود عکس تکراری"""
    return hashlib.sha256(image_bytes).hexdigest()


def compress_image(image_bytes: bytes) -> bytes:
    """
    تغییر سایز به حداکثر ۸۰۰ پیکسل و فشرده‌سازی با حفظ کیفیت تا سقف ۱۵۰ کیلوبایت
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # حذف اطلاعات اضافی (EXIF) و تبدیل به RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # تغییر ابعاد متناسب
        img.thumbnail(
            (config.PHOTO_MAX_DIMENSION, config.PHOTO_MAX_DIMENSION),
            Image.Resampling.LANCZOS
        )

        quality = config.PHOTO_QUALITY
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)

        # اگر حجم هنوز بالای ۱۵۰ کیلوبایت بود، کیفیت به صورت پلکانی کاهش می‌یابد
        while output.tell() > config.COMPRESSED_MAX_KB * 1024 and quality > 30:
            quality -= 5
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)

        return output.getvalue()


def save_user_photo(user_id: int, image_bytes: bytes) -> Dict[str, Any]:
    """ذخیره عکس پردازش شده کاربر"""
    if len(image_bytes) > config.MAX_PHOTO_SIZE_MB * 1024 * 1024:
        return {"success": False, "error": f"حجم عکس نباید بیشتر از {config.MAX_PHOTO_SIZE_MB} مگابایت باشد."}

    if not validate_image_bytes(image_bytes):
        return {"success": False, "error": "فرمت فایل نامعتبر است. فقط JPG, PNG, WEBP مجاز است."}

    try:
        photo_hash = compute_hash(image_bytes)
        compressed_bytes = compress_image(image_bytes)

        file_name = f"{user_id}.jpg"
        file_path = config.PHOTOS_DIR / file_name

        with open(file_path, "wb") as f:
            f.write(compressed_bytes)

        return {
            "success": True,
            "filename": file_name,
            "path": f"/photos/{file_name}",
            "hash": photo_hash
        }
    except Exception as e:
        return {"success": False, "error": f"خطا در پردازش تصویر: {str(e)}"}


def delete_photo(user_id: int):
    """حذف عکس پروفایل کاربر"""
    file_path = config.PHOTOS_DIR / f"{user_id}.jpg"
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass