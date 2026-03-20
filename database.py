import sqlite3
import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "inkognito.db"

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
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
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        password_hash = self._hash_password(password)
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # Username already exists

    def authenticate_user(self, username, password):
        password_hash = self._hash_password(password)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
                (username, password_hash)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def save_report_metadata(self, user_id, report_id, subject_name, generated_at, report_path):
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO reports (user_id, report_id, subject_name, generated_at, report_path) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, report_id, subject_name, generated_at, report_path)
            )
            conn.commit()

    def get_user_reports(self, user_id):
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT report_id, subject_name, generated_at, report_path FROM reports WHERE user_id = ? ORDER BY generated_at DESC",
                (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_user_by_id(self, user_id):
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT id, username FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None
