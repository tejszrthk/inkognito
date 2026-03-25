import os
import hashlib
import uuid
import sqlite3
import bcrypt
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Optional PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DEFAULT_DB_PATH = Path(__file__).parent / "inkognito.db"

class Database:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.is_postgres = False
        
        if self.db_url and self.db_url.startswith("postgres"):
            if not HAS_POSTGRES:
                raise ImportError("psycopg2 is required for PostgreSQL support but not installed.")
            self.is_postgres = True
        
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            # PostgreSQL connection
            result = urlparse(self.db_url)
            db_name = result.path.lstrip('/')
            conn = psycopg2.connect(
                database=db_name,
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            return conn
        else:
            # SQLite connection
            conn = sqlite3.connect(self.db_url or DEFAULT_DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    def _init_db(self):
        if self.is_postgres:
            conn = self._get_connection()
            cur = conn.cursor()
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        report_id TEXT UNIQUE NOT NULL,
                        subject_name TEXT NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        report_path TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                conn.commit()
            finally:
                cur.close()
                conn.close()
        else:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        report_id TEXT UNIQUE NOT NULL,
                        subject_name TEXT NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        report_path TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                conn.commit()

    def _hash_password(self, password: str) -> str:
        # Use bcrypt for production security
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _check_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            # Fallback for old SHA256 hashes if any exist during transition
            # This is optional but helps with the sudden switch
            sha_hash = hashlib.sha256(password.encode()).hexdigest()
            return sha_hash == hashed

    def register_user(self, username, password):
        password_hash = self._hash_password(password)
        try:
            conn = self._get_connection()
            if self.is_postgres:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                        (username, password_hash)
                    )
                    user_id = cur.fetchone()[0]
                    conn.commit()
                    return user_id
                finally:
                    cur.close()
                    conn.close()
            else:
                with conn:
                    cursor = conn.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, password_hash)
                    )
                    return cursor.lastrowid
        except Exception:
            return None  # Username already exists or DB error

    def authenticate_user(self, username, password):
        conn = self._get_connection()
        if self.is_postgres:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                if row and self._check_password(password, row['password_hash']):
                    return {"id": row['id'], "username": row['username']}
            finally:
                cur.close()
                conn.close()
        else:
            with conn:
                row = conn.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
                if row and self._check_password(password, row['password_hash']):
                    return dict(row)
        return None

    def save_report_metadata(self, user_id, report_id, subject_name, generated_at, report_path):
        conn = self._get_connection()
        if self.is_postgres:
            cur = conn.cursor()
            try:
                cur.execute(
                    """INSERT INTO reports (user_id, report_id, subject_name, generated_at, report_path) 
                       VALUES (%s, %s, %s, %s, %s)""",
                    (user_id, report_id, subject_name, generated_at, report_path)
                )
                conn.commit()
            finally:
                cur.close()
                conn.close()
        else:
            with conn:
                conn.execute(
                    """INSERT INTO reports (user_id, report_id, subject_name, generated_at, report_path) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, report_id, subject_name, generated_at, report_path)
                )

    def get_user_reports(self, user_id):
        conn = self._get_connection()
        if self.is_postgres:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(
                    "SELECT report_id, subject_name, generated_at, report_path FROM reports WHERE user_id = %s ORDER BY generated_at DESC",
                    (user_id,)
                )
                return [dict(row) for row in cur.fetchall()]
            finally:
                cur.close()
                conn.close()
        else:
            with conn:
                rows = conn.execute(
                    "SELECT report_id, subject_name, generated_at, report_path FROM reports WHERE user_id = ? ORDER BY generated_at DESC",
                    (user_id,)
                ).fetchall()
                return [dict(row) for row in rows]

    def get_user_by_id(self, user_id):
        conn = self._get_connection()
        if self.is_postgres:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if row: return dict(row)
            finally:
                cur.close()
                conn.close()
        else:
            with conn:
                row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
                if row: return dict(row)
        return None
