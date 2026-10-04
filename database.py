import sqlite3
import os
from datetime import date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "hamdam.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                name TEXT DEFAULT '',
                age INTEGER DEFAULT 0,
                gender TEXT DEFAULT '',
                city TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                education TEXT DEFAULT '',
                job TEXT DEFAULT '',
                interests TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                is_complete INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                daily_likes_used INTEGER DEFAULT 0,
                last_like_date TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER NOT NULL,
                to_user INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user, to_user)
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1 INTEGER NOT NULL,
                user2 INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1, user2)
            );

            CREATE TABLE IF NOT EXISTS seen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                seen_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, seen_user_id)
            );

            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blocker INTEGER NOT NULL,
                blocked INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blocker, blocked)
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter INTEGER NOT NULL,
                reported INTEGER NOT NULL,
                reason TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


def upsert_user(user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
    with get_conn() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET username=?, first_name=?, last_name=? WHERE user_id=?",
                (username, first_name, last_name, user_id)
            )
        else:
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                (user_id, username, first_name, last_name)
            )


def get_user(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_profile(user_id: int, data: dict):
    allowed = ["name", "age", "gender", "city", "bio", "goal", "education", "job", "interests", "photo_url", "is_complete"]
    fields = []
    values = []
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        return
    values.append(user_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", values)


def get_candidates(user_id: int, gender: str = "", city: str = "", min_age: int = 16, max_age: int = 60, limit: int = 20) -> list:
    with get_conn() as conn:
        query = """
            SELECT * FROM users
            WHERE user_id != ?
              AND is_complete = 1
              AND is_banned = 0
              AND age BETWEEN ? AND ?
              AND user_id NOT IN (SELECT seen_user_id FROM seen WHERE user_id = ?)
              AND user_id NOT IN (SELECT blocked FROM blocks WHERE blocker = ?)
              AND user_id NOT IN (SELECT blocker FROM blocks WHERE blocked = ?)
        """
        params = [user_id, min_age, max_age, user_id, user_id, user_id]

        if gender:
            query += " AND gender = ?"
            params.append(gender)
        if city:
            query += " AND city = ?"
            params.append(city)

        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def add_seen(user_id: int, seen_user_id: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO seen (user_id, seen_user_id) VALUES (?, ?)", (user_id, seen_user_id))


def reset_seen(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM seen WHERE user_id = ?", (user_id,))


def add_like(from_user: int, to_user: int) -> bool:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO likes (from_user, to_user) VALUES (?, ?)", (from_user, to_user))
        mutual = conn.execute(
            "SELECT id FROM likes WHERE from_user = ? AND to_user = ?", (to_user, from_user)
        ).fetchone()
        if mutual:
            u1, u2 = min(from_user, to_user), max(from_user, to_user)
            conn.execute("INSERT OR IGNORE INTO matches (user1, user2) VALUES (?, ?)", (u1, u2))
            return True
        return False


def check_and_reset_daily_likes(user_id: int) -> int:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute("SELECT daily_likes_used, last_like_date FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row and row["last_like_date"] == today:
            return row["daily_likes_used"]
        conn.execute("UPDATE users SET daily_likes_used = 0, last_like_date = ? WHERE user_id = ?", (today, user_id))
        return 0


def increment_daily_likes(user_id: int):
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET daily_likes_used = daily_likes_used + 1, last_like_date = ? WHERE user_id = ?",
            (today, user_id)
        )


def get_matches(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.* FROM users u
            INNER JOIN matches m ON (
                (m.user1 = ? AND m.user2 = u.user_id) OR
                (m.user2 = ? AND m.user1 = u.user_id)
            )
            WHERE u.is_banned = 0
            ORDER BY m.created_at DESC
        """, (user_id, user_id)).fetchall()
        return [dict(r) for r in rows]


def add_block(blocker: int, blocked: int):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO blocks (blocker, blocked) VALUES (?, ?)", (blocker, blocked))
        u1, u2 = min(blocker, blocked), max(blocker, blocked)
        conn.execute("DELETE FROM matches WHERE user1 = ? AND user2 = ?", (u1, u2))
        conn.execute("DELETE FROM likes WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)",
                      (blocker, blocked, blocked, blocker))


def add_report(reporter: int, reported: int, reason: str = ""):
    with get_conn() as conn:
        conn.execute("INSERT INTO reports (reporter, reported, reason) VALUES (?, ?, ?)", (reporter, reported, reason))
