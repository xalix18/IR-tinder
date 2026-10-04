import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler

import config
import auth
import database as db
import image_handler

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

tg_app: Application = None


# --- Telegram Bot Handlers ---
async def cmd_start(update: Update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💝 ورود به همدم", web_app=WebAppInfo(url=config.WEBAPP_URL))]
    ])
    await update.message.reply_text(
        "سلام! 👋\nبه ربات **همدم** خوش آمدید.\n\nبرای شروع، روی دکمه زیر بزنید:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# --- Auth Helper ---
def authenticate(request: Request) -> dict | None:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return auth.validate_telegram_data(init_data)


# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    db.init_db()

    global tg_app
    tg_app = Application.builder().token(config.BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", cmd_start))

    await tg_app.initialize()
    await tg_app.start()

    webhook_url = f"{config.WEBAPP_URL}/telegram-webhook"
    await tg_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
    print(f"✅ Webhook set to: {webhook_url}")

    yield

    await tg_app.stop()
    await tg_app.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.process_update(update)
    except Exception as e:
        print(f"Webhook error: {e}")
    return {"status": "ok"}


@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/api/init")
async def api_init(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    user_id = tg_user["user_id"]
    db.upsert_user(user_id, tg_user.get("username", ""), tg_user.get("first_name", ""), tg_user.get("last_name", ""))
    user = db.get_user(user_id)

    daily_used = db.check_and_reset_daily_likes(user_id)

    user_data = dict(user) if user else {}
    if user_data.get("photo_url"):
        user_data["photo_url"] = f"/photos/{user_data['photo_url']}"

    return {
        "success": True,
        "user": user_data,
        "is_admin": user_id in config.ADMIN_IDS,
        "daily_likes_used": daily_used,
        "constants": {
            "cities": config.CITIES,
            "genders": config.GENDERS,
            "goals": config.GOALS,
            "education": config.EDUCATION_LEVELS,
            "interests": config.INTERESTS,
            "daily_like_limit": config.DAILY_LIKE_LIMIT
        }
    }


@app.post("/api/profile")
async def api_profile(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "داده نامعتبر"}

    age = body.get("age", 0)
    if not isinstance(age, int) or age < 16 or age > 60:
        return {"success": False, "error": "سن باید بین ۱۶ تا ۶۰ باشد"}

    name = str(body.get("name", "")).strip()
    if not name:
        return {"success": False, "error": "نام الزامی است"}

    gender = str(body.get("gender", "")).strip()
    if gender not in ("male", "female"):
        return {"success": False, "error": "جنسیت نامعتبر"}

    city = str(body.get("city", "")).strip()
    if not city:
        return {"success": False, "error": "شهر الزامی است"}

    interests_list = body.get("interests", [])
    if isinstance(interests_list, list):
        interests_str = ",".join(interests_list[:5])
    else:
        interests_str = ""

    data = {
        "name": name[:30],
        "age": age,
        "gender": gender,
        "city": city,
        "bio": str(body.get("bio", ""))[:300],
        "goal": str(body.get("goal", ""))[:50],
        "education": str(body.get("education", ""))[:50],
        "job": str(body.get("job", ""))[:40],
        "interests": interests_str,
        "is_complete": 1
    }

    db.update_profile(tg_user["user_id"], data)
    return {"success": True}


@app.post("/api/photo")
async def api_photo(request: Request, photo: UploadFile = File(...)):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    file_bytes = await photo.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        return {"success": False, "error": "حجم فایل بیش از حد مجاز"}

    filename = image_handler.compress_and_save(file_bytes, photo.filename)
    if not filename:
        return {"success": False, "error": "خطا در پردازش تصویر"}

    db.update_profile(tg_user["user_id"], {"photo_url": filename})
    return {"success": True, "photo_url": f"/photos/{filename}"}


@app.post("/api/candidates")
async def api_candidates(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    try:
        filters = await request.json()
    except Exception:
        filters = {}

    candidates = db.get_candidates(
        user_id=tg_user["user_id"],
        gender=filters.get("gender", ""),
        city=filters.get("city", ""),
        min_age=int(filters.get("min_age", 16)),
        max_age=int(filters.get("max_age", 60)),
        limit=20
    )

    for c in candidates:
        if c.get("photo_url"):
            c["photo_url"] = f"/photos/{c['photo_url']}"
        for sensitive_key in ["daily_likes_used", "last_like_date", "is_banned", "created_at"]:
            c.pop(sensitive_key, None)

    return {"success": True, "candidates": candidates}


@app.post("/api/swipe")
async def api_swipe(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "داده نامعتبر"}

    target_id = body.get("target_id")
    action = body.get("action")

    if not target_id or action not in ("like", "pass"):
        return {"success": False, "error": "درخواست نامعتبر"}

    user_id = tg_user["user_id"]
    db.add_seen(user_id, target_id)

    if action == "pass":
        return {"success": True, "is_match": False}

    daily_used = db.check_and_reset_daily_likes(user_id)
    if daily_used >= config.DAILY_LIKE_LIMIT:
        return {"success": False, "error": f"سقف لایک روزانه ({config.DAILY_LIKE_LIMIT}) تمام شده است"}

    is_match = db.add_like(user_id, target_id)
    db.increment_daily_likes(user_id)

    if is_match:
        try:
            my_user = db.get_user(user_id)
            target_user = db.get_user(target_id)

            my_name = my_user.get("name", "کاربر") if my_user else "کاربر"
            target_name = target_user.get("name", "کاربر") if target_user else "کاربر"

            my_username = my_user.get("username", "") if my_user else ""
            target_username = target_user.get("username", "") if target_user else ""

            msg_to_target = f"🎉 تبریک! شما و **{my_name}** با هم مچ شدید!"
            if my_username:
                msg_to_target += f"\n\n💬 ارسال پیام: @{my_username}"

            msg_to_me = f"🎉 تبریک! شما و **{target_name}** با هم مچ شدید!"
            if target_username:
                msg_to_me += f"\n\n💬 ارسال پیام: @{target_username}"

            await tg_app.bot.send_message(chat_id=target_id, text=msg_to_target, parse_mode="Markdown")
            await tg_app.bot.send_message(chat_id=user_id, text=msg_to_me, parse_mode="Markdown")
        except Exception as e:
            print(f"Match notification error: {e}")

    return {"success": True, "is_match": is_match}


@app.post("/api/reset-seen")
async def api_reset_seen(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)
    db.reset_seen(tg_user["user_id"])
    return {"success": True}


@app.get("/api/matches")
async def api_matches(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    matches = db.get_matches(tg_user["user_id"])
    for m in matches:
        if m.get("photo_url"):
            m["photo_url"] = f"/photos/{m['photo_url']}"
        for sensitive_key in ["daily_likes_used", "last_like_date", "is_banned", "created_at"]:
            m.pop(sensitive_key, None)

    return {"success": True, "matches": matches}


@app.post("/api/block")
async def api_block(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "داده نامعتبر"}

    blocked_id = body.get("blocked_id")
    if not blocked_id:
        return {"success": False, "error": "شناسه کاربر نامعتبر"}

    db.add_block(tg_user["user_id"], blocked_id)
    return {"success": True}


@app.post("/api/report")
async def api_report(request: Request):
    tg_user = authenticate(request)
    if not tg_user:
        return JSONResponse({"success": False, "error": "احراز هویت ناموفق"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return {"success": False, "error": "داده نامعتبر"}

    reported_id = body.get("reported_id")
    reason = str(body.get("reason", ""))[:200]

    if not reported_id:
        return {"success": False, "error": "شناسه کاربر نامعتبر"}

    db.add_report(tg_user["user_id"], reported_id, reason)
    return {"success": True}
