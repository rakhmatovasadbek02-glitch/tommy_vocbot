import psycopg2
import os

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        role TEXT DEFAULT 'student',
        score REAL DEFAULT 0,
        wrong INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        unit TEXT,
        score REAL,
        total INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS word_stats (
        user_id BIGINT,
        word TEXT,
        correct INTEGER DEFAULT 0,
        wrong INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, word)
    )
    """)

    conn.commit()

def add_user(user_id, username):
    cursor.execute("""
    INSERT INTO users (user_id, username)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username))
    conn.commit()

def set_role(user_id, role):
    cursor.execute("UPDATE users SET role=%s WHERE user_id=%s", (role, user_id))
    conn.commit()

def get_role(user_id):
    cursor.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else "student"

def is_teacher(user_id):
    return get_role(user_id) in ["teacher", "editor"]

def is_editor(user_id):
    return get_role(user_id) == "editor"

def get_leaderboard():
    cursor.execute("""
    SELECT username, score FROM users
    ORDER BY score DESC LIMIT 10
    """)
    return cursor.fetchall()