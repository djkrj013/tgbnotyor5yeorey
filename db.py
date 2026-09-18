import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            age INTEGER,
            gender TEXT,
            looking_for TEXT,
            city TEXT,
            bio TEXT,
            photo_id TEXT,
            is_active INTEGER DEFAULT 1,
            is_banned INTEGER DEFAULT 0,
            fake_likes INTEGER DEFAULT 0,
            boosted_until TEXT,
            created_at TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            reaction TEXT NOT NULL, -- 'like' / 'dislike'
            created_at TEXT,
            UNIQUE(from_id, to_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_id INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'open', -- 'open' / 'resolved'
            created_at TEXT
        )
        """)


def now_iso():
    return datetime.utcnow().isoformat()


# ---------- Пользователи ----------

def user_exists(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone()
        return row is not None


def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def create_or_update_user(user_id, username, name, age, gender, looking_for, city, bio, photo_id):
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone()
        if exists:
            conn.execute("""
                UPDATE users SET username=?, name=?, age=?, gender=?, looking_for=?,
                city=?, bio=?, photo_id=?, is_active=1 WHERE id=?
            """, (username, name, age, gender, looking_for, city, bio, photo_id, user_id))
        else:
            conn.execute("""
                INSERT INTO users (id, username, name, age, gender, looking_for, city, bio,
                photo_id, is_active, is_banned, fake_likes, boosted_until, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,1,0,0,NULL,?)
            """, (user_id, username, name, age, gender, looking_for, city, bio, photo_id, now_iso()))


def set_active(user_id: int, active: bool):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))


def set_banned(user_id: int, banned: bool):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_banned=? WHERE id=?", (1 if banned else 0, user_id))


def is_banned(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["is_banned"])


def boost_user(user_id: int, hours: int):
    until = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE users SET boosted_until=? WHERE id=?", (until, user_id))
    return until


def add_fake_likes(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET fake_likes = fake_likes + ? WHERE id=?", (amount, user_id))


# ---------- Просмотр анкет ----------

def get_next_profile(user_id: int):
    """Возвращает следующую подходящую анкету, которую пользователь ещё не оценивал."""
    with get_conn() as conn:
        row = conn.execute("""
            SELECT u.* FROM users u
            WHERE u.id != ?
              AND u.is_active = 1
              AND u.is_banned = 0
              AND u.id NOT IN (SELECT to_id FROM reactions WHERE from_id = ?)
            ORDER BY
              CASE WHEN u.boosted_until IS NOT NULL AND u.boosted_until > ? THEN 0 ELSE 1 END,
              RANDOM()
            LIMIT 1
        """, (user_id, user_id, now_iso())).fetchone()
        return row


def get_likes_count(user_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM reactions WHERE to_id=? AND reaction='like'", (user_id,)
        ).fetchone()
        real_likes = row["c"] if row else 0
        u = conn.execute("SELECT fake_likes FROM users WHERE id=?", (user_id,)).fetchone()
        fake = u["fake_likes"] if u else 0
        return real_likes + fake


def add_reaction(from_id: int, to_id: int, reaction: str) -> bool:
    """Сохраняет реакцию. Возвращает True, если это привело к взаимному лайку (мэтчу)."""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reactions (from_id, to_id, reaction, created_at) VALUES (?,?,?,?)
            ON CONFLICT(from_id, to_id) DO UPDATE SET reaction=excluded.reaction, created_at=excluded.created_at
        """, (from_id, to_id, reaction, now_iso()))
        if reaction == "like":
            mutual = conn.execute(
                "SELECT 1 FROM reactions WHERE from_id=? AND to_id=? AND reaction='like'",
                (to_id, from_id)
            ).fetchone()
            return mutual is not None
        return False


# ---------- Жалобы ----------

def add_report(reporter_id: int, reported_id: int, reason: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reports (reporter_id, reported_id, reason, status, created_at)
            VALUES (?,?,?, 'open', ?)
        """, (reporter_id, reported_id, reason, now_iso()))


def get_open_reports(limit=10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reports WHERE status='open' ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def resolve_report(report_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE reports SET status='resolved' WHERE id=?", (report_id,))


# ---------- Статистика для админки ----------

def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        active = conn.execute("SELECT COUNT(*) c FROM users WHERE is_active=1 AND is_banned=0").fetchone()["c"]
        banned = conn.execute("SELECT COUNT(*) c FROM users WHERE is_banned=1").fetchone()["c"]
        likes = conn.execute("SELECT COUNT(*) c FROM reactions WHERE reaction='like'").fetchone()["c"]
        matches_row = conn.execute("""
            SELECT COUNT(*) c FROM reactions r1
            JOIN reactions r2 ON r1.from_id = r2.to_id AND r1.to_id = r2.from_id
            WHERE r1.reaction='like' AND r2.reaction='like' AND r1.from_id < r1.to_id
        """).fetchone()
        matches = matches_row["c"]
        open_reports = conn.execute("SELECT COUNT(*) c FROM reports WHERE status='open'").fetchone()["c"]
        return {
            "total_users": total,
            "active_profiles": active,
            "banned_users": banned,
            "total_likes": likes,
            "total_matches": matches,
            "open_reports": open_reports,
        }


def list_recent_users(limit=15):
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, age, is_active, is_banned FROM users ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()


# ---------- Рассылка ----------

def get_all_user_ids(exclude_banned: bool = True):
    """Возвращает ID всех пользователей бота (по умолчанию без забаненных) для рассылки."""
    with get_conn() as conn:
        if exclude_banned:
            rows = conn.execute("SELECT id FROM users WHERE is_banned = 0").fetchall()
        else:
            rows = conn.execute("SELECT id FROM users").fetchall()
        return [row["id"] for row in rows]
