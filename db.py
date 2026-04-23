import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL or "postgres" not in DATABASE_URL:
    raise Exception(f"❌ DATABASE_URL is wrong: {DATABASE_URL}")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        role TEXT DEFAULT 'student',
        score REAL DEFAULT 0
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

    conn.commit()

def add_user(user_id, username):
    cursor.execute("""
    INSERT INTO users (user_id, username)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO NOTHING
    """, (user_id, username))
    conn.commit()

def get_leaderboard():
    cursor.execute("""
    SELECT username, score FROM users
    ORDER BY score DESC LIMIT 10
    """)
    return cursor.fetchall()