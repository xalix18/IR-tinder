import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN در فایل .env یافت نشد!")

# آدرس عمومی سرور (برای وب‌هوک و مینی‌اپ)
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000").rstrip("/")
PORT = int(os.getenv("PORT", 8000))

# لیست ادمین‌های اصلی
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# مسیرها
PHOTOS_DIR = BASE_DIR / "photos"
PHOTOS_DIR.mkdir(exist_ok=True)

BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

# تنظیمات عکس
MAX_PHOTO_SIZE_MB = 5
COMPRESSED_MAX_KB = 150
PHOTO_MAX_DIMENSION = 800
PHOTO_QUALITY = 75
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# تنظیمات اپلیکیشن
DAILY_LIKE_LIMIT = 50
MIN_AGE = 16
MAX_AGE = 60
DAILY_SUGGESTION_COUNT = 15

# لیست‌های انتخابی
CITIES = [
    "تهران", "اصفهان", "شیراز", "تبریز", "مشهد",
    "اهواز", "کرج", "قم", "کرمانشاه", "ارومیه",
    "رشت", "زاهدان", "همدان", "کرمان", "یزد",
    "اردبیل", "بندرعباس", "اراک", "زنجان", "سنندج",
    "قزوین", "خرم‌آباد", "گرگان", "ساری", "بجنورد",
    "بیرجند", "ایلام", "شهرکرد", "یاسوج", "بوشهر",
    "سمنان", "سایر"
]

GENDERS = {
    "male": "👨 پسر",
    "female": "👩 دختر"
}

INTERESTS = [
    "🎵 موسیقی", "🎬 فیلم و سریال", "📚 کتاب و مطالعه",
    "⚽ ورزش", "🎮 گیمینگ", "✈️ سفر و گردشگری",
    "🍳 آشپزی", "💻 تکنولوژی", "📸 عکاسی",
    "🎨 هنر و نقاشی", "🧘 یوگا و مدیتیشن", "🐱 حیوانات",
    "🌿 طبیعت", "💼 کسب‌وکار", "📝 نویسندگی",
    "🎤 پادکست", "🏋️ بدنسازی", "🎭 تئاتر"
]

GOALS = [
    "👫 دوستی ساده",
    "💬 هم‌صحبت",
    "🤝 رابطه جدی",
    "📚 هم‌فکری و یادگیری",
    "💼 ارتباط کاری"
]

EDUCATION_LEVELS = [
    "🎓 دیپلم", "📘 کاردانی", "📗 کارشناسی",
    "📕 کارشناسی ارشد", "📒 دکتری", "🏫 حوزوی", "📖 سایر"
]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS