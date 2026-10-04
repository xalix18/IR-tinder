import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import config

DB_PATH = Path(__file__).resolve().parent / "social.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")  # کارایی بالا برای درخواست‌های همزمان وب
    return conn


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                photo_path TEXT,
                photo_hash TEXT,
                bio TEXT,
                job TEXT,
                education TEXT,
                interests TEXT,
                goal TEXT,
                reg_state TEXT,
                is_complete INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_banned INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                last_active TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                created_at TEXT,
                UNIQUE(from_user, to_user)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 INTEGER,
                user2 INTEGER,
                created_at TEXT,
                UNIQUE(user1, user2)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker INTEGER,
                blocked INTEGER,
                created_at TEXT,
                UNIQUE(blocker, blocked)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter INTEGER,
                reported INTEGER,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen (
                user_id INTEGER,
                seen_user INTEGER,
                created_at TEXT,
                PRIMARY KEY (user_id, seen_user)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_likes (
                user_id INTEGER,
                like_date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY(user_id, like_date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                target_id INTEGER,
                details TEXT,
                created_at TEXT
            )
        """)

        conn.commit()


# ===================== عملیات کاربران =====================

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_or_get_user(user_id: int, username: str = None, name: str = "") -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            conn.execute("""
                INSERT INTO users (user_id, username, name, created_at, updated_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, name, now, now, now))
            conn.commit()
            return get_user(user_id)
        else:
            # بروزرسانی یوزرنیم
            if username and user["username"] != username:
                conn.execute("UPDATE users SET username = ?, updated_at = ? WHERE user_id = ?",
                             (username, now, user_id))
                conn.commit()
            return dict(user)


def update_user_profile(user_id: int, data: dict):
    data["updated_at"] = datetime.utcnow().isoformat()
    if "interests" in data and isinstance(data["interests"], list):
        data["interests"] = json.dumps(data["interests"], ensure_ascii=False)

    keys = [k for k in data.keys() if k not in ("user_id", "created_at")]
    set_clause = ", ".join(f"{k} = ?" for k in keys)
    values = [data[k] for k in keys] + [user_id]

    with get_db() as conn:
        conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
        conn.commit()


def update_last_active(user_id: int):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (now, user_id))
        conn.commit()


# ===================== کاندیداها و سوایپ =====================

def find_candidates(user_id: int, filters: dict, limit: int = 15) -> List[Dict[str, Any]]:
    query = """
        SELECT u.* FROM users u
        WHERE u.user_id != ?
          AND u.is_complete = 1
          AND u.is_active = 1
          AND u.is_banned = 0
          AND u.user_id NOT IN (SELECT seen_user FROM seen WHERE user_id = ?)
          AND u.user_id NOT IN (SELECT blocked FROM blocks WHERE blocker = ?)
          AND u.user_id NOT IN (SELECT blocker FROM blocks WHERE blocked = ?)
          AND u.user_id NOT IN (SELECT to_user FROM likes WHERE from_user = ?)
    """
    params = [user_id, user_id, user_id, user_id, user_id]

    if filters.get("city") and filters["city"] != "همه":
        query += " AND u.city = ?"
        params.append(filters["city"])

    if filters.get("gender") and filters["gender"] in ("male", "female"):
        query += " AND u.gender = ?"
        params.append(filters["gender"])

    if filters.get("min_age"):
        query += " AND u.age >= ?"
        params.append(int(filters["min_age"]))

    if filters.get("max_age"):
        query += " AND u.age <= ?"
        params.append(int(filters["max_age"]))

    query += " ORDER BY u.last_active DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["interests"] = json.loads(d["interests"]) if d["interests"] else []
            except Exception:
                d["interests"] = []
            result.append(d)
        return result


def mark_seen(user_id: int, seen_id: int):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen (user_id, seen_user, created_at) VALUES (?, ?, ?)",
            (user_id, seen_id, now)
        )
        conn.commit()


def reset_seen(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM seen WHERE user_id = ?", (user_id,))
        conn.commit()


# ===================== لایک و مچ =====================

def add_like(from_user: int, to_user: int) -> bool:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO likes (from_user, to_user, created_at) VALUES (?, ?, ?)",
            (from_user, to_user, now)
        )

        # بررسی مچ بودن
        reciprocal = conn.execute(
            "SELECT 1 FROM likes WHERE from_user = ? AND to_user = ?",
            (to_user, from_user)
        ).fetchone()

        if reciprocal:
            u1, u2 = sorted([from_user, to_user])
            conn.execute(
                "INSERT OR IGNORE INTO matches (user1, user2, created_at) VALUES (?, ?, ?)",
                (u1, u2, now)
            )
            conn.commit()
            return True

        conn.commit()
        return False


def get_matches(user_id: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        query = """
            SELECT u.* FROM users u
            JOIN matches m ON (u.user_id = m.user1 OR u.user_id = m.user2)
            WHERE (m.user1 = ? OR m.user2 = ?) AND u.user_id != ?
            ORDER BY m.created_at DESC
        """
        rows = conn.execute(query, (user_id, user_id, user_id)).fetchall()
        matches = []
        for r in rows:
            d = dict(r)
            try:
                d["interests"] = json.loads(d["interests"]) if d["interests"] else []
            except Exception:
                d["interests"] = []
            matches.append(d)
        return matches


def get_today_like_count(user_id: int) -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_db() as conn:
        row = conn.execute(
            "SELECT count FROM daily_likes WHERE user_id = ? AND like_date = ?",
            (user_id, today)
        ).fetchone()
        return row["count"] if row else 0


def increment_daily_like(user_id: int):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_db() as conn:
        conn.execute("""
            INSERT INTO daily_likes (user_id, like_date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, like_date) DO UPDATE SET count = count + 1
        """, (user_id, today))
        conn.commit()


# ===================== بلاک و گزارش =====================

def block_user(blocker: int, blocked: int):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blocks (blocker, blocked, created_at) VALUES (?, ?, ?)",
            (blocker, blocked, now)
        )
        # حذف مچ در صورت وجود
        u1, u2 = sorted([blocker, blocked])
        conn.execute("DELETE FROM matches WHERE user1 = ? AND user2 = ?", (u1, u2))
        conn.commit()


def add_report(reporter: int, reported: int, reason: str):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO reports (reporter, reported, reason, created_at) VALUES (?, ?, ?, ?)",
            (reporter, reported, reason, now)
        )
        conn.commit()


# ===================== تنظیمات =====================

def get_setting(key: str, default: str = "") -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()