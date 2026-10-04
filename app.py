import os
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException, Depends, Header, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

import config
import database as db
import image_handler as ih
import auth

# لاگ‌ها
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ساخت شیء تلگرام
bot_app = Application.builder().token(config.BOT_TOKEN).build()


# ===================== هندلرهای ربات تلگرام =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام خوش‌آمدگویی همراه با دکمه ورود به مینی‌اپ"""
    user = update.effective_user
    db.create_or_get_user(user.id, user.username, user.first_name)

    webapp_url = config.WEBAPP_URL
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 ورود به برنامه آشنایی", web_app=WebAppInfo(url=webapp_url))]
    ])

    text = (
        f"سلام {user.first_name} عزیز! 👋\n\n"
        "به نسل جدید ربات دوستیابی و آشنایی تلگرام خوش آمدید.\n"
        "برای شروع و دیدن افراد، روی دکمه زیر کلیک کنید:"
    )
    await update.message.reply_text(text, reply_markup=kb)


bot_app.add_handler(CommandHandler("start", start_command))


# ===================== چرخه حیات وب‌سرور =====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # مقداردهی دیتابیس
    db.init_db()
    logger.info("Database initialized.")

    # راه‌اندازی ربات تلگرام و تنظیم وب‌هوک
    await bot_app.initialize()
    await bot_app.start()

    webhook_url = f"{config.WEBAPP_URL}/telegram-webhook"
    try:
        await bot_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook set to: {webhook_url}")
    except Exception as e:
        logger.warning(f"Could not set webhook automatically: {e}")

    yield

    # خاموش شدن
    await bot_app.stop()
    await bot_app.shutdown()


app = FastAPI(title="Telegram Social MiniApp", lifespan=lifespan)

# مسیر فایل‌های استاتیک و قالب‌ها
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ===================== میدلور احراز هویت تلگرام =====================

async def get_current_user(x_telegram_init_data: Optional[str] = Header(None)) -> dict:
    """اعتبارسنجی امن توکن initData ارسالی از مینی‌اپ تلگرام"""
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram authentication data.")

    tg_user = auth.validate_telegram_data(x_telegram_init_data)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication signature.")

    user_id = tg_user["id"]
    username = tg_user.get("username")
    first_name = tg_user.get("first_name", "")

    user = db.create_or_get_user(user_id, username, first_name)
    db.update_last_active(user_id)
    return user


# ===================== مدل‌های ورودی (Pydantic) =====================

class ProfileUpdateModel(BaseModel):
    name: str
    age: int
    gender: str
    city: str
    bio: Optional[str] = ""
    job: Optional[str] = ""
    education: Optional[str] = ""
    interests: List[str] = []
    goal: Optional[str] = ""


class SwipeModel(BaseModel):
    target_id: int
    action: str  # 'like' or 'pass'


class FilterModel(BaseModel):
    city: Optional[str] = "همه"
    gender: Optional[str] = "any"
    min_age: Optional[int] = 16
    max_age: Optional[int] = 60


class ActionModel(BaseModel):
    target_id: int
    reason: Optional[str] = ""


# ===================== روت‌های وب و صفحات =====================

@app.get("/", response_class=HTMLResponse)
async def serve_miniapp(request: Request):
    """صفحه اصلی مینی‌اپ"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    """ارائه عکس‌های ذخیره‌شده کاربران"""
    file_path = config.PHOTOS_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "Photo not found"})


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    """دریافت وب‌هوک‌های ارسالی از سرورهای تلگرام"""
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {"ok": False}


# ===================== ای‌پی‌آی‌های مینی‌اپ (API) =====================

@app.get("/api/init")
async def api_init(user: dict = Depends(get_current_user)):
    """دریافت اطلاعات اولیه کاربر و گزینه‌های فرم‌ها"""
    interests_list = []
    if user.get("interests"):
        try:
            interests_list = json.loads(user["interests"])
        except Exception:
            interests_list = []

    user_data = dict(user)
    user_data["interests"] = interests_list
    user_data["is_admin"] = config.is_admin(user["user_id"])

    return {
        "user": user_data,
        "options": {
            "cities": config.CITIES,
            "genders": config.GENDERS,
            "interests": config.INTERESTS,
            "goals": config.GOALS,
            "education_levels": config.EDUCATION_LEVELS,
            "min_age": config.MIN_AGE,
            "max_age": config.MAX_AGE,
            "daily_like_limit": config.DAILY_LIKE_LIMIT,
            "today_likes": db.get_today_like_count(user["user_id"])
        }
    }


@app.post("/api/profile")
async def api_update_profile(data: ProfileUpdateModel, user: dict = Depends(get_current_user)):
    """بروزرسانی یا تکمیل پروفایل کاربر"""
    user_id = user["user_id"]

    if not (config.MIN_AGE <= data.age <= config.MAX_AGE):
        raise HTTPException(status_code=400, detail=f"سن باید بین {config.MIN_AGE} تا {config.MAX_AGE} باشد.")

    update_dict = data.dict()
    update_dict["is_complete"] = 1  # تکمیل ثبت‌نام

    db.update_user_profile(user_id, update_dict)
    return {"success": True, "message": "پروفایل با موفقیت ذخیره شد."}


@app.post("/api/photo")
async def api_upload_photo(photo: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """آپلود عکس پروفایل جدید"""
    user_id = user["user_id"]
    content = await photo.read()

    res = ih.save_user_photo(user_id, content)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["error"])

    db.update_user_profile(user_id, {
        "photo_path": res["path"],
        "photo_hash": res["hash"]
    })

    return {"success": True, "photo_url": res["path"]}


@app.post("/api/candidates")
async def api_get_candidates(filters: FilterModel, user: dict = Depends(get_current_user)):
    """دریافت کارت‌های افراد برای سوایپ"""
    user_id = user["user_id"]
    candidates = db.find_candidates(user_id, filters.dict(), limit=config.DAILY_SUGGESTION_COUNT)
    return {"candidates": candidates}


@app.post("/api/swipe")
async def api_swipe(swipe: SwipeModel, user: dict = Depends(get_current_user)):
    """مدیریت سوایپ کاربر (لایک یا رد کردن)"""
    user_id = user["user_id"]
    target_id = swipe.target_id

    db.mark_seen(user_id, target_id)

    if swipe.action == "pass":
        return {"success": True, "match": False}

    if swipe.action == "like":
        # بررسی سقف لایک روزانه
        today_count = db.get_today_like_count(user_id)
        if today_count >= config.DAILY_LIKE_LIMIT:
            raise HTTPException(status_code=429, detail="به سقف ۵۰ لایک روزانه رسیده‌اید. لطفاً فردا تلاش کنید.")

        is_match = db.add_like(user_id, target_id)
        db.increment_daily_like(user_id)

        target_user = db.get_user(target_id)

        # اگر مچ شدند، برای هر دو نفر در تلگرام پیام ارسال می‌شود
        if is_match and target_user:
            try:
                user_link = f"https://t.me/{user['username']}" if user.get("username") else "(بدون نام کاربری)"
                target_link = f"https://t.me/{target_user['username']}" if target_user.get("username") else "(بدون نام کاربری)"

                # پیام به کاربر جاری
                await bot_app.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 <b>تبریک! شما با {target_user['name']} مَچ شدید!</b>\n\nمی‌توانید گفت‌وگو را آغاز کنید:\n👉 {target_link}",
                    parse_mode="HTML"
                )
                # پیام به کاربر مقابل
                await bot_app.bot.send_message(
                    chat_id=target_id,
                    text=f"🎉 <b>تبریک! شما با {user['name']} مَچ شدید!</b>\n\nمی‌توانید گفت‌وگو را آغاز کنید:\n👉 {user_link}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to send match telegram message: {e}")

        return {
            "success": True,
            "match": is_match,
            "matched_user": {
                "name": target_user["name"],
                "username": target_user.get("username"),
                "photo_path": target_user.get("photo_path")
            } if is_match and target_user else None
        }

    raise HTTPException(status_code=400, detail="اکشن نامعتبر است.")


@app.post("/api/reset-seen")
async def api_reset_seen(user: dict = Depends(get_current_user)):
    """شروع مجدد و دیدن افراد از ابتدا"""
    db.reset_seen(user["user_id"])
    return {"success": True, "message": "لیست افراد با موفقیت از ابتدا بازنشانی شد."}


@app.get("/api/matches")
async def api_get_matches(user: dict = Depends(get_current_user)):
    """دریافت لیست تمام مچ‌ها"""
    matches = db.get_matches(user["user_id"])
    return {"matches": matches}


@app.post("/api/block")
async def api_block(action: ActionModel, user: dict = Depends(get_current_user)):
    """بلاک کردن یک کاربر"""
    db.block_user(user["user_id"], action.target_id)
    return {"success": True, "message": "کاربر با موفقیت مسدود شد."}


@app.post("/api/report")
async def api_report(action: ActionModel, user: dict = Depends(get_current_user)):
    """گزارش تخلف کاربر"""
    db.add_report(user["user_id"], action.target_id, action.reason or "گزارش از مینی اپ")
    return {"success": True, "message": "گزارش شما ثبت و بررسی خواهد شد."}