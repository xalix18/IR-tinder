import os
import uuid
from io import BytesIO
from PIL import Image

import config

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)


def compress_and_save(file_bytes: bytes, original_filename: str = "photo.jpg") -> str | None:
    try:
        img = Image.open(BytesIO(file_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        max_dim = config.MAX_PHOTO_DIM
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)

        unique_name = f"{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(PHOTOS_DIR, unique_name)

        quality = 85
        while quality >= 30:
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            size_kb = buffer.tell() / 1024
            if size_kb <= config.MAX_PHOTO_SIZE_KB:
                with open(save_path, "wb") as f:
                    f.write(buffer.getvalue())
                return unique_name
            quality -= 5

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=30, optimize=True)
        with open(save_path, "wb") as f:
            f.write(buffer.getvalue())
        return unique_name

    except Exception as e:
        print(f"Image compression error: {e}")
        return None
